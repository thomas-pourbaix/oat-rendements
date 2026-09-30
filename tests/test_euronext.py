from datetime import datetime

import pytest

from oat.euronext import _parse_trade


def _cell(shown: str, tooltip: str) -> str:
    return f'<div class="text-right pointer tooltipDesign">{shown}<span class="tooltiptext">{tooltip}</span></div>'


@pytest.mark.parametrize("shown, tooltip, expected", [
    ("11 Mar 2026", "09:00 CET", datetime(2026, 3, 11, 9, 0)),   # échange ancien
    ("09:00 CEST", "30 Sep 2026", datetime(2026, 9, 30, 9, 0)),  # échange du jour même : présentation inversée
    ("-", "", None),                                              # jamais échangé
])
def test_last_trade_is_read_whatever_the_layout(shown, tooltip, expected):
    assert _parse_trade(_cell(shown, tooltip)) == expected, "la date du dernier échange doit être lue dans les deux présentations"
