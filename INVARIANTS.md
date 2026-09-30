# Invariants catalogue

> **Generic doctrine** (what an invariant is, invariant ↔ test mutual coverage, the `INV-XXX` /
> criticality / status format, lifecycle, audit pass) lives in Thomas's `invariants` skill.
> **Read it before editing this file.** Only this project's catalogue is kept here.
>
> Do not read the code to write a test: read the invariant and write the test that checks
> **that** rule. If an invariant is ambiguous, raise a question rather than interpreting the code.

**Scope**: yield computation (`oat/yields.py`) and Euronext data fetching (`oat/euronext.py`).

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
