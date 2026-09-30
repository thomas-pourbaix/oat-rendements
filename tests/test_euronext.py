from datetime import datetime

from oat.euronext import _parse_trade


def _cell(shown: str, tooltip: str) -> str:
    return f'<div class="text-right pointer tooltipDesign">{shown}<span class="tooltiptext">{tooltip}</span></div>'


def test_parse_older_trade():
    assert _parse_trade(_cell("11 Mar 2026", "09:00 CET")) == datetime(2026, 3, 11, 9, 0)


def test_parse_trade_of_the_day():
    # Euronext swaps the layout for today's trades: time shown, date in the tooltip
    assert _parse_trade(_cell("09:00 CEST", "30 Sep 2026")) == datetime(2026, 9, 30, 9, 0)


def test_parse_no_trade():
    assert _parse_trade(_cell("-", "")) is None
