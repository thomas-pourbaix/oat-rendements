# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end tests of the order guard (garde-fou/), run in Chromium on a stand-in of the bank's order page."""

import functools
import json
import re
import shutil
import threading
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

import pytest
from playwright.sync_api import Page, expect

GUARD = Path(__file__).resolve().parent.parent / "garde-fou"
YEAR = datetime.now().year


def _bond(isin, price, maturity_year, traded_days_ago):
    return {
        "isin": isin, "price": price, "maturity": f"{maturity_year}-04-25",
        "last_trade": (datetime.now() - timedelta(days=traded_days_ago)).isoformat(timespec="seconds"),
    }


BONDS = [
    _bond("FR0000000011", 82.82, YEAR + 29, 1),   # long bond far below par, like the 4 % 2055
    _bond("FR0000000012", 98.25, YEAR + 2, 1),    # short bond near par
    _bond("FR0000000013", 98.25, YEAR + 2, 11),   # quote just past the 10-day limit
    {**_bond("FR0000000014", 98.25, YEAR + 2, 1), "price": '<img src=x onerror="document.body.dataset.pwned=1">'},
]
LONG = {"isin": "FR0000000011", "label": f"OAT 4%05-2504{YEAR + 29}"}
SHORT = {"isin": "FR0000000012", "label": f"OAT 2,4%25-2504{(YEAR + 2) % 100:02d}"}


@pytest.fixture(scope="session")
def guard_url(tmp_path_factory):
    """Serve a copy of garde-fou/ with a hand-made oats.json."""
    root = tmp_path_factory.mktemp("guard")
    shutil.copytree(GUARD, root, dirs_exist_ok=True)
    (root / "data").mkdir()
    (root / "data" / "oats.json").write_text(json.dumps({"bonds": BONDS}))
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *args: None
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/test-page.html"
    server.shutdown()


@pytest.fixture
def order(page: Page, guard_url):
    """Open the order page with the given order fields and wait for the guard's panel."""
    def open_order(**fields):
        page.goto(f"{guard_url}?{urlencode(fields)}")
        expect(page.locator("#gf-panel")).to_be_visible()
        return page
    return open_order


def try_to_confirm(page: Page):
    """Every way of sending the order: real click (forced through the neutralised style), synthetic click, Enter."""
    confirm = page.locator("#btnConfirmer")
    confirm.click(force=True)
    confirm.dispatch_event("click")
    confirm.focus()
    page.keyboard.press("Enter")


def blocked_reasons(page: Page) -> str:
    expect(page.locator("#gf-panel.block")).to_be_visible()
    return page.locator("#gf-panel").inner_text()


class TestLimitFarFromTheMarketIsBlocked:
    """INV-016: an order whose limit is more than 1.5 points worse than the last traded price is blocked."""

    def test_buy_far_above(self, order):
        assert "14,18 points trop cher" in blocked_reasons(order(**LONG, limit="97,00")), "INV-016: buy limit 14 points above"

    def test_sell_far_below(self, order):
        assert "trop bas" in blocked_reasons(order(**LONG, limit="70,00", side="Vendre")), "INV-016: sell limit 13 points below"

    def test_within_the_gap_is_not_blocked(self, order):
        expect(order(**LONG, limit="84,00").locator("#gf-panel.ask")).to_be_visible()


class TestBankWarningBlocks:
    """INV-017: an order is blocked whenever the bank shows its "écart de cours important" warning."""

    def test_bank_warning(self, order):
        assert "écart de cours" in blocked_reasons(order(**LONG, limit="83,00", warning="1")), "INV-017"


class TestUnverifiablePriceBlocks:
    """INV-018: an order is blocked when the bond's last traded price is unknown or older than 10 days."""

    def test_stale_quote(self, order):
        page = order(isin="FR0000000013", label="OAT 1%25-250428", limit="98,00")
        assert "inconnu ou trop ancien" in blocked_reasons(page), "INV-018: 11-day-old quote"

    def test_unlisted_isin(self, order):
        page = order(isin="FR0000000099", label="OAT 1%25-250428", limit="98,00")
        assert "inconnu ou trop ancien" in blocked_reasons(page), "INV-018: ISIN not in oats.json"


class TestOrderWithoutLimitBlocks:
    """INV-019: an order without a price limit (market order) is blocked."""

    def test_market_order(self, order):
        assert "sans limite" in blocked_reasons(order(**SHORT, limit="none")), "INV-019"


class TestNothingSendsAnOrderBeforeItIsAllowed:
    """INV-020: until the guard allows the order, no click or key on "Confirmer" sends it."""

    def test_blocked_order(self, order):
        page = order(**LONG, limit="97,00")
        try_to_confirm(page)
        expect(page.locator("#sent")).to_be_hidden()

    def test_order_waiting_for_the_year(self, order):
        page = order(**SHORT, limit="98,50")
        try_to_confirm(page)
        expect(page.locator("#sent")).to_be_hidden()


class TestIntendedYearMustMatchTheBond:
    """INV-021: the maturity year typed by the user must be the bond's; a mismatch blocks the order with no second attempt."""

    def test_wrong_year(self, order):
        page = order(**SHORT, limit="98,50")
        page.locator("#gf-year").press_sequentially(str(YEAR + 29))
        assert "Ce n'est pas le bon titre" in blocked_reasons(page), "INV-021: wrong year blocks"
        assert page.locator("#gf-year").count() == 0, "INV-021: no second attempt"


class TestSummaryIsHiddenWhileAskingTheYear:
    """INV-022: while the guard asks for the intended year, the order summary is blurred."""

    def test_blurred(self, order):
        expect(order(**SHORT, limit="98,50").locator("#esdtblCaractOrd")).to_have_class(re.compile(r"\bgf-blurred\b"))


class TestConfirmUnlocksOnlyAfterTheDelay:
    """INV-023: once the right year is typed, "Confirmer" sends the order only after a 5-second delay."""

    def test_unlock(self, order):
        page = order(**SHORT, limit="98,50")
        page.locator("#gf-year").press_sequentially(str(YEAR + 2))
        expect(page.locator("#gf-panel.pass")).to_be_visible()
        try_to_confirm(page)
        expect(page.locator("#sent")).to_be_hidden()
        expect(page.locator("#gf-countdown")).to_have_text("« Confirmer » est débloqué.", timeout=8000)
        page.locator("#btnConfirmer").click()
        expect(page.locator("#sent")).to_be_visible()


class TestBankActionsStayAvailableWhenBlocked:
    """INV-024: while an order is blocked, the bank's other actions on the page (such as "Modifier") still work."""

    def test_modify_after_block(self, order):
        page = order(**LONG, limit="97,00")
        expect(page.locator("#gf-panel.block")).to_be_visible()
        page.locator("#btnModifier").click()
        expect(page.locator("#modified")).to_be_visible()
        expect(page.locator("#sent")).to_be_hidden()


class TestTamperedDataNeverReachesThePage:
    """INV-025: a row of oats.json with unexpected types is treated as an unknown price, and never inserts markup into the bank's page."""

    def test_markup_in_price(self, order):
        page = order(isin="FR0000000014", label="OAT 1%25-250428", limit="98,00")
        assert "inconnu ou trop ancien" in blocked_reasons(page), "INV-025: tampered row means unknown price"
        assert page.locator("#gf-panel img").count() == 0, "INV-025: no markup from the data file"
        assert page.evaluate("document.body.dataset.pwned") is None, "INV-025: no script from the data file"
