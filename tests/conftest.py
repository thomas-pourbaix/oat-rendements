# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

import functools
import json
import os
import shutil
import threading
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"


def _bond(isin, kind, years, ytm, traded_days_ago):
    trade = None if traded_days_ago is None else (datetime.now() - timedelta(days=traded_days_ago)).isoformat(timespec="seconds")
    return {
        "isin": isin, "name": isin, "ticker": None, "kind": kind, "coupon": 1.0,
        "maturity": (datetime.now() + timedelta(days=round(years * 365.25))).date().isoformat(),
        "years": years, "price": 98.0, "accrued": 0.1, "last_trade": trade, "ytm": ytm,
        "url": f"https://live.euronext.com/fr/product/bonds/{isin}-XPAR",
    }


# Hand-made data set: each bond sits on one side of a filter boundary.
BONDS = [
    _bond("FR0000000001", "nominal", 2.0, 0.030, 0),              # in window, fresh
    _bond("FR0000000002", "nominal", 2.9, 0.036, 1),              # in window (± 1 year), fresh, best
    _bond("FR0000000003", "nominal", 3.2, 0.040, 0),              # out of window
    _bond("FR0000000004", "nominal", 1.5, 0.050, 45),             # in window, stale quote
    _bond("FR0000000005", "nominal", 2.5, 0.060, None),           # in window, never traded
    _bond("FR0000000006", "inflation_euro", 2.0, 0.010, 0),       # in window, unchecked kind by default
]


@pytest.fixture(scope="session")
def site_url(tmp_path_factory):
    """Serve a copy of site/ with the fixture data set instead of the real oats.json."""
    root = tmp_path_factory.mktemp("site")
    shutil.copytree(SITE, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data"))
    (root / "data").mkdir()
    (root / "data" / "oats.json").write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds") + "+00:00",
        "settlement": datetime.now().date().isoformat(),
        "count": len(BONDS),
        "bonds": BONDS,
    }))
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *args: None
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Use a preinstalled Chromium when one is provided (e.g. a sandbox without `playwright install`)
    path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    return {**browser_type_launch_args, **({"executable_path": path} if path else {})}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "permissions": ["clipboard-read", "clipboard-write"]}
