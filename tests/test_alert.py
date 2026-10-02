# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

import json

import pytest

from oat import alert

ISIN = "FR0000000099"
SECRETS = {
    "ALERT_ISIN": ISIN,
    "ALERT_THRESHOLD": "98",
    "SMTP_USER": "owner@example.com",
    "SMTP_PASSWORD": "app-password-123",
    "ALERT_EMAIL": "inbox@example.com",
}


class _FakeSMTP:
    sent = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        pass

    def send_message(self, msg):
        _FakeSMTP.sent.append(msg)


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run the alert on a one-bond data file; return (exit code, mails sent)."""
    def _run(price, isin=ISIN):
        bond = {"isin": isin, "name": "OAT TEST", "maturity": "2055-04-25", "price": price,
                "last_trade": "2026-10-01T09:00:00", "url": f"https://live.euronext.com/fr/product/bonds/{isin}-XPAR"}
        data = tmp_path / "oats.json"
        data.write_text(json.dumps({"bonds": [bond]}), encoding="utf-8")
        for key, value in SECRETS.items():
            monkeypatch.setenv(key, value)
        _FakeSMTP.sent = []
        code = alert.main(["--data", str(data)], smtp_factory=_FakeSMTP)
        return code, _FakeSMTP.sent
    return _run


class TestAlertFiresIffPriceReachesThreshold:
    """INV-026: a mail is sent if and only if the watched bond's last price is at or above the threshold."""

    def test_no_mail_below_threshold(self, run):
        code, sent = run(97.99)
        assert code == 0
        assert sent == [], "INV-026: no mail while the price is below the threshold"

    @pytest.mark.parametrize("price", [98.0, 101.5])
    def test_mail_at_or_above_threshold(self, run, price):
        code, sent = run(price)
        assert code == 0
        assert len(sent) == 1, "INV-026: one mail once the price reaches the threshold"
        assert sent[0]["To"] == "inbox@example.com", "INV-026: the mail goes to the configured recipient"


class TestAlertNeverLogsItsConfiguration:
    """INV-027: the job log never shows the watched ISIN, threshold, price, addresses or password."""

    @pytest.mark.parametrize("price", [80.1, 98.76])
    def test_log_is_clean(self, run, capsys, price):
        run(price)
        out = capsys.readouterr()
        log = out.out + out.err
        for secret in [ISIN, "98", str(price), "owner@example.com", "inbox@example.com", "app-password-123"]:
            assert secret not in log, f"INV-027: '{secret}' leaked into the public job log"


class TestMissingWatchedBondFails:
    """INV-028: a watched bond missing from the data fails the job."""

    def test_missing_bond(self, run):
        code, sent = run(99.0, isin="FR0000000001")
        assert code != 0, "INV-028: a missing watched bond must fail the job"
        assert sent == []
