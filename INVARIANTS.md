# Invariants catalogue

> **Generic doctrine** (what an invariant is, invariant ↔ test mutual coverage, the `INV-XXX` /
> criticality / status format, lifecycle, audit pass) lives in Thomas's `invariants` skill.
> **Read it before editing this file.** Only this project's catalogue is kept here.
>
> Do not read the code to write a test: read the invariant and write the test that checks
> **that** rule. If an invariant is ambiguous, raise a question rather than interpreting the code.

**Scope**: yield computation (`oat/yields.py`), Euronext data fetching (`oat/euronext.py`) and the page (`site/`).

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
