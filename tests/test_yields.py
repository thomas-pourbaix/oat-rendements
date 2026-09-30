from datetime import date

import pytest

from oat.yields import accrued_interest, add_business_days, coupon_dates, dirty_price, yield_to_maturity


class TestYieldDiscountsCashFlowsToDirtyPrice:
    """INV-001: the yield discounts the future cash flows back to the dirty price paid."""

    def test_zero_coupon_matches_closed_form(self):
        settle, mat = date(2026, 11, 25), date(2031, 11, 25)  # exactly 5 years
        y = yield_to_maturity(80.0, 0.0, settle, mat)
        assert y == pytest.approx((100 / 80) ** (1 / 5) - 1, abs=1e-9), "INV-001: zero coupon yield is (100/P)^(1/n) - 1"

    def test_par_bond_on_coupon_date_yields_its_coupon(self):
        settle, mat = date(2026, 5, 25), date(2033, 5, 25)
        assert yield_to_maturity(100.0, 3.0, settle, mat) == pytest.approx(0.03, abs=1e-9), "INV-001: a par bond yields its coupon"

    def test_price_yield_roundtrip_between_coupons(self):
        settle, mat, cpn = date(2026, 9, 29), date(2035, 11, 25), 3.5
        clean = dirty_price(0.0342, cpn, settle, mat) - accrued_interest(cpn, settle, mat)
        assert yield_to_maturity(clean, cpn, settle, mat) == pytest.approx(0.0342, abs=1e-9), "INV-001: price -> yield -> price roundtrip"


class TestAccruedInterestIsActAct:
    """INV-002: accrued interest is the coupon prorated on actual days over the actual coupon period."""

    def test_accrued_interest_act_act(self):
        # 3 % paid on 25 May: on 25 November, 184 days accrued out of 365
        assert accrued_interest(3.0, date(2026, 11, 25), date(2033, 5, 25)) == pytest.approx(3.0 * 184 / 365), "INV-002"


class TestCouponScheduleFollowsMaturityAnniversaries:
    """INV-003: coupons fall on the maturity anniversaries; the schedule after settlement ends at maturity."""

    def test_coupon_dates(self):
        prev, future = coupon_dates(date(2026, 9, 29), date(2028, 5, 25))
        assert prev == date(2026, 5, 25), "INV-003: last paid coupon is the latest anniversary before settlement"
        assert future == [date(2027, 5, 25), date(2028, 5, 25)], "INV-003: future coupons are the anniversaries up to maturity"


class TestSettlementIsTwoBusinessDays:
    """INV-004: settlement is two business days after the trade date, weekends skipped."""

    def test_settlement_skips_weekend(self):
        assert add_business_days(date(2026, 9, 25), 2) == date(2026, 9, 29), "INV-004: Friday -> Tuesday"
