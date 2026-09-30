from datetime import datetime

import pytest

from oat import euronext
from oat.euronext import _parse_trade


def _cell(shown: str, tooltip: str) -> str:
    return f'<div class="text-right pointer tooltipDesign">{shown}<span class="tooltiptext">{tooltip}</span></div>'


class TestLastTradeIsReadWhateverTheLayout:
    """INV-005: the last trade date is read whichever of the two Euronext layouts is used, and never invented."""

    @pytest.mark.parametrize("shown, tooltip, expected", [
        ("11 Mar 2026", "09:00 CET", datetime(2026, 3, 11, 9, 0)),   # older trade
        ("09:00 CEST", "30 Sep 2026", datetime(2026, 9, 30, 9, 0)),  # trade of the day: layout swapped
        ("-", "", None),                                              # never traded
    ])
    def test_parse_trade(self, shown, tooltip, expected):
        assert _parse_trade(_cell(shown, tooltip)) == expected, "INV-005: last trade date must be read in both layouts"


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class _FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)

    def post(self, *args, **kwargs):
        return _FakeResponse(self.payloads.pop(0))


class TestEmptyPageIsNeverTakenAsEndOfList:
    """INV-006: an intermittent empty page from Euronext is retried, never taken as the end of the bond list."""

    EMPTY = {"iTotalRecords": None, "iTotalDisplayRecords": None, "aaData": []}
    GOOD = {"iTotalRecords": 1, "aaData": [["row"]]}

    def test_empty_page_is_retried(self, monkeypatch):
        monkeypatch.setattr(euronext.time, "sleep", lambda s: None)
        page = euronext._post(_FakeSession([self.EMPTY, self.GOOD]), 0)
        assert page == self.GOOD, "INV-006: an empty page must be retried"

    def test_persistent_empty_page_fails_loudly(self, monkeypatch):
        monkeypatch.setattr(euronext.time, "sleep", lambda s: None)
        with pytest.raises(RuntimeError):
            euronext._post(_FakeSession([self.EMPTY] * 6), 0)
