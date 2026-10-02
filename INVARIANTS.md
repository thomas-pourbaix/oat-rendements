# Invariants catalogue

> **Generic doctrine** (what an invariant is, invariant ↔ test mutual coverage, the `INV-XXX` /
> criticality / status format, lifecycle, audit pass) lives in Thomas's `invariants` skill.
> **Read it before editing this file.** Only this project's catalogue is kept here.
>
> Do not read the code to write a test: read the invariant and write the test that checks
> **that** rule. If an invariant is ambiguous, raise a question rather than interpreting the code.

**Scope**: yield computation (`oat/yields.py`), Euronext data fetching (`oat/euronext.py`), the page (`site/`), calculator included, and the order guard (`garde-fou/`).

**Legend**: criticality `C` / `H` / `M` / `L` · status ✅ verified · ⚠️ partial · ❌ untested (debt) · 🐛 known bug.

---

## 1. Yield computation

### INV-001 [C] ✅ The yield discounts the future cash flows back to the dirty price paid
The returned yield `r` satisfies: clean price + accrued interest = sum of future coupons and
redemption at 100, each discounted at `(1 + r) ** t`, `t` in coupon periods (ACT/ACT ICMA).
- **Why**: it is the number the page displays; a wrong yield is a wrong answer to the user's question.
- **Coverage**: `tests/test_yields.py::TestYieldDiscountsCashFlowsToDirtyPrice` (roundtrip, plus two
  external oracles: zero coupon closed form `(100/P)^(1/n) - 1`, par bond yielding its coupon).

### INV-002 [H] ✅ Accrued interest is ACT/ACT ICMA
Accrued interest = coupon × (days since the last coupon) / (days in the current coupon period).
- **Why**: the buyer pays the accrued interest on top of the quoted price; it enters the yield.
- **Coverage**: `tests/test_yields.py::TestAccruedInterestIsActAct`.

### INV-003 [H] ✅ Coupons fall on the maturity anniversaries
Future coupon dates are the anniversaries of the maturity date strictly after settlement, the last
one being the maturity; the last paid coupon is the latest anniversary on or before settlement.
- **Why**: OAT coupons are annual, paid on the maturity anniversary; a shifted schedule skews both
  accrued interest and discounting.
- **Coverage**: `tests/test_yields.py::TestCouponScheduleFollowsMaturityAnniversaries`.

### INV-004 [M] ✅ Settlement is two business days after the trade date
Weekends are skipped (public holidays are not modelled).
- **Why**: accrued interest and discounting start from the settlement date, not the trade date.
- **Coverage**: `tests/test_yields.py::TestSettlementIsTwoBusinessDays`.
- **Known limit**: TARGET2 holidays are ignored (one day off at most, a few times a year).

## 2. Euronext data (external input contract)

### INV-005 [H] ✅ The last trade date is read whichever layout Euronext uses
Euronext shows either `date` + time in the tooltip (older trade) or `time` + date in the tooltip
(trade of the day). Both yield the trade date and time; a cell without a date (`-`) yields `null`,
never an invented date.
- **Why**: the page hides quotes older than 30 days; a missing date hides the bond. Bug observed on
  2026-09-30: 56 of 57 nominal OATs traded that day had no date and disappeared from the page.
- **Coverage**: `tests/test_euronext.py::TestLastTradeIsReadWhateverTheLayout`.

### INV-006 [H] ✅ An empty Euronext page is never taken as the end of the bond list
The directory API intermittently answers `{"iTotalRecords": null, "aaData": []}`. Such a page is
retried; if it persists, the build fails instead of publishing a truncated list.
- **Why**: stopping on it silently drops every bond on the following pages.
- **Coverage**: `tests/test_euronext.py::TestEmptyPageIsNeverTakenAsEndOfList`.

## 3. Page

Checked in a real browser on the hand-made data set of `tests/conftest.py`.

### INV-007 [H] ✅ The table shows exactly the bonds in the horizon window, of a checked kind
A bond is shown if and only if its kind is checked and `|years - horizon| <= window`
(freshness filter aside, cf. INV-008).
- **Why**: it is the page's question ("what can I buy for this horizon?"); a missing bond is a missed
  option, an extra one a wrong answer.
- **Coverage**: `tests/test_page.py::TestShownBondsMatchTheHorizonWindowAndKinds`.

### INV-008 [H] ✅ With the freshness filter on, no quote older than 30 days or unknown is shown
A bond whose last trade is older than 30 days, or has no known last trade, is hidden.
- **Why**: a yield computed on an old price says nothing about today's buying price.
- **Coverage**: `tests/test_page.py::TestFreshFilterHidesOldOrMissingQuotes`.
- **Note**: this filter hid almost every OAT when the trade date was lost upstream (cf. INV-005).

### INV-009 [M] ✅ The best yield announced and highlighted is the highest among the shown bonds
- **Why**: the summary line is what the user reads first.
- **Coverage**: `tests/test_page.py::TestBestYieldIsTheHighestShown`.

### INV-010 [M] ✅ Clicking an ISIN copies exactly that ISIN to the clipboard
The ISIN is shown again afterwards.
- **Why**: the ISIN is what the user types into their broker's order form.
- **Coverage**: `tests/test_page.py::TestClickingAnIsinCopiesIt`.

## 4. Calculator ("Mon prix d'achat" tab)

### INV-011 [C] ✅ The browser computes the same yield as the Python code
`site/yields.js` (used by the calculator) and `oat/yields.py` (used for the table) give the same yield
(within 1e-10), accrued interest and T+2 settlement for the same bond, price and settlement date.
- **Why**: the calculation exists twice (the page is static, the user's price is only known in the
  browser); without this rule the two would drift apart and the tabs would disagree.
- **Coverage**: `tests/test_page.py::TestBrowserYieldMatchesPython` (zero coupon, par bond, between
  coupons, above par, maturity on 29 February).

### INV-012 [H] ✅ The calculator gives the yield at the price typed by the user
For a listed ISIN (pasted with spaces or in lower case) and a price typed in % of face value (decimal
comma accepted), the yield shown is the yield to maturity at that price, settled two business days
from today.
- **Why**: the user does not always buy at the last traded price.
- **Coverage**: `tests/test_page.py::TestCalculatorGivesTheYieldAtTheUserPrice`.

### INV-013 [H] ✅ The calculator never shows a yield without a valid ISIN and price
An invalid or unlisted ISIN, a missing, non-numeric or zero price, or an invalid fee (non-numeric,
negative, 100 % or more; an empty fee field is valid and means no fees) shows a message saying what is
missing, and no yield.
- **Why**: a yield computed on a wrong input looks like a real answer.
- **Coverage**: `tests/test_page.py::TestCalculatorNeverShowsAYieldWithoutValidInput`.

### INV-014 [H] ✅ The net yield includes the fees, charged on the dirty price
With a fee rate typed, total cost = (clean price + accrued interest) × (1 + fee rate), and the net
yield is the yield to maturity of a bond whose dirty price is that total cost.
- **Why**: on a short maturity, fees change the yield noticeably (3.50 % → 3.40 % on the order below);
  brokers charge them on the amount paid, accrued interest included.
- **Coverage**: `tests/test_page.py::TestNetYieldIncludesTheFees`, with an external oracle: a CIC order
  of 2026-09-30 (OAT 0.75 % 25/11/2028 at 94.4 %, 0.2 % fees) whose statement shows a unit cost price
  of 0.9522.
- **Known limit**: that broker figure is too coarse to tell fees on the dirty price from fees on the
  clean price (0.51 € apart on that order); the exact convention is pinned by a formula assertion.

## 5. Explainer page (`site/comprendre.html`)

### INV-015 [M] ✅ Every figure of the worked example is what the yield code computes
Accrued interest, dirty price, fees, total paid, gain at maturity, gross and net yields, and the three
resale scenarios are recomputed by the tests with `oat/yields.py` and must appear as written.
- **Why**: the figures are written by hand in the page; a typo would teach the wrong thing.
- **Coverage**: `tests/test_page.py::TestExplainerExampleMatchesTheCode`.

## 6. Order guard (`garde-fou/`, browser extension on the bank's order page)

Design rule shared by this section: the guard is tuned for the user's worst state (tired, rushed).
"Blocked" means the guard's panel shows the reason and "Confirmer" stays dead, with no override;
the only way out is the bank's own "Modifier" or "Abandonner".

### INV-016 [C] ✅ An order whose limit is more than 1.5 points worse than the last price is blocked
Buy limit above the last traded price + 1.5 points, or sell limit below it − 1.5 points, from the
published `oats.json`.
- **Why**: a limit far from the market can fill at that limit on a thin order book, and the bank's own
  check only warns, or rejects beyond a wider gap.
- **Coverage**: `tests/test_guard.py::TestLimitFarFromTheMarketIsBlocked` (above, below, and a limit
  inside the gap that is not blocked).

### INV-017 [H] ✅ An order is blocked whenever the bank shows its "écart de cours important" warning
- **Why**: the bank's warning is an orange banner, next to another banner shown on every order; it is
  easy to stop seeing.
- **Coverage**: `tests/test_guard.py::TestBankWarningBlocks`.

### INV-018 [H] ✅ An order is blocked when the last price is unknown or older than 10 days
- **Why**: without a recent price the limit cannot be checked; the guard fails closed.
- **Coverage**: `tests/test_guard.py::TestUnverifiablePriceBlocks` (11-day-old quote, unlisted ISIN).

### INV-019 [H] ✅ An order without a price limit is blocked
- **Why**: a market order on a thinly traded bond can fill at any price.
- **Coverage**: `tests/test_guard.py::TestOrderWithoutLimitBlocks`.

### INV-020 [C] ✅ Until the guard allows the order, nothing sends it
No real click, synthetic click or Enter on "Confirmer" submits the order while it is blocked or
waiting for the intended year.
- **Why**: a block that a stray click or keypress gets through protects nothing.
- **Coverage**: `tests/test_guard.py::TestNothingSendsAnOrderBeforeItIsAllowed`. Defence in depth:
  the button is disabled and events aimed at it are swallowed in the capture phase; the mutation test
  fails only when both are removed.

### INV-021 [C] ✅ The intended maturity year must be the bond's, with one attempt
The user types the maturity year they intend; a year other than the bond's blocks the order and the
field disappears.
- **Why**: a wrong ISIN is invisible on a price check when the wrong bond trades near the intended
  price; it shows up as a mismatch between intention and selection.
- **Coverage**: `tests/test_guard.py::TestIntendedYearMustMatchTheBond`.

### INV-022 [M] ✅ The order summary is blurred while the year is asked
- **Why**: otherwise the year is copied from the screen instead of recalled from the intention.
- **Coverage**: `tests/test_guard.py::TestSummaryIsHiddenWhileAskingTheYear`.

### INV-023 [M] ✅ "Confirmer" unlocks only 5 seconds after the right year is typed
- **Why**: a short pause with the bond, maturity, limit and price shown in plain words, before the
  irreversible click.
- **Coverage**: `tests/test_guard.py::TestConfirmUnlocksOnlyAfterTheDelay`.

### To write (backlog)
- An unreadable order summary (bank page changed) blocks the order: implemented, not tested; the test
  page always has a summary.
