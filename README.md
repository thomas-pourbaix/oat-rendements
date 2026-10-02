# OAT yield to maturity

Small web app listing every OAT (French government bond) listed on Euronext Paris with its **annual yield if held to maturity**. Pick a horizon of *n* years and the page shows the bonds maturing around that horizon. The page is in French.

**Live: https://thomas-pourbaix.github.io/oat-rendements/**

## How it works

1. Every weekday evening, a GitHub Action runs `python -m oat.build`:
   - [oat/euronext.py](oat/euronext.py) fetches the bonds issued by "REPUBLIC OF FRANCE" and their last price from the Euronext Live JSON API;
   - [oat/figi.py](oat/figi.py) fetches each bond's coupon and kind (nominal OAT, OATi, OAT€i, strip) from the public [OpenFIGI](https://www.openfigi.com/api) API;
   - [oat/yields.py](oat/yields.py) computes the yield to maturity: annual coupon, ACT/ACT ICMA accrued interest, T+2 business days settlement;
   - the result is written to `site/data/oats.json`.
2. The `site/` folder (static HTML/JS) is published on GitHub Pages; filtering by horizon happens in the browser, and so does the "Mon prix d'achat" calculator ([site/yields.js](site/yields.js), a port of `oat/yields.py`; a test keeps both identical). [site/comprendre.html](site/comprendre.html) explains, on a real order, how buying and selling an OAT works.

Tests: pytest for the Python code, and [Playwright](https://playwright.dev/python/) (through pytest) for the page, which runs in a real Chromium on a hand-made data set.

Expected behaviour is catalogued in [INVARIANTS.md](INVARIANTS.md), changes in [CHANGELOG.md](CHANGELOG.md).

## Running locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
.venv/bin/python -m oat.build
python3 -m http.server 8765 -d site
```

## Order guard (browser extension)

[garde-fou/](garde-fou/) is a Chrome extension that steps in on CIC's order confirmation page for an OAT. It is tuned for the user's worst state (tired, rushed): an anomaly **blocks** the order, with no button to override it. The only way out is the bank's own "Modifier" or "Abandonner".

- The order is blocked when the bank shows "écart de cours important", when the limit is more than 1.5 points away from the last traded price (from the published `oats.json`), when that price is unknown or older than 10 days, when the order has no limit, or when the order summary cannot be read.
- Otherwise the summary is blurred and the user must type the maturity year they intend. One attempt only: a year that differs from the selected bond blocks the order. A matching year unblocks "Confirmer" after 5 seconds.

Install: `chrome://extensions`, developer mode, "Load unpacked", pick `garde-fou/`. Its tests (`tests/test_guard.py`) run it in Chromium on [garde-fou/test-page.html](garde-fou/test-page.html), a stand-in for the bank's page.

## Limits

- The yield uses the **last traded price**, not the ask price of the order book: on a thinly traded bond the gap can be significant. The date of the price is shown.
- **Gross** yield: no brokerage fees, no taxes.
- For OATi / OAT€i, the displayed yield is a real yield (before inflation).
- Not investment advice.

## License

Copyright (C) 2026 Thomas Pourbaix

This program is free software, released under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-only). Any modified version made available, including over a network, must publish its source code under the same license.
