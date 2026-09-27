from datetime import date

import pytest

from oat.yields import accrued_interest, add_business_days, coupon_dates, dirty_price, yield_to_maturity


def test_zero_coupon_matches_closed_form():
    settle, mat = date(2026, 11, 25), date(2031, 11, 25)  # 5 ans pile
    y = yield_to_maturity(80.0, 0.0, settle, mat)
    assert y == pytest.approx((100 / 80) ** (1 / 5) - 1, abs=1e-9)


def test_par_bond_on_coupon_date_yields_its_coupon():
    settle, mat = date(2026, 5, 25), date(2033, 5, 25)
    assert yield_to_maturity(100.0, 3.0, settle, mat) == pytest.approx(0.03, abs=1e-9)


def test_price_yield_roundtrip_between_coupons():
    settle, mat, cpn = date(2026, 9, 29), date(2035, 11, 25), 3.5
    clean = dirty_price(0.0342, cpn, settle, mat) - accrued_interest(cpn, settle, mat)
    assert yield_to_maturity(clean, cpn, settle, mat) == pytest.approx(0.0342, abs=1e-9)


def test_accrued_interest_act_act():
    # 3 % payé le 25 mai : au 25 novembre, 184 jours courus sur 365
    assert accrued_interest(3.0, date(2026, 11, 25), date(2033, 5, 25)) == pytest.approx(3.0 * 184 / 365)


def test_coupon_dates():
    prev, future = coupon_dates(date(2026, 9, 29), date(2028, 5, 25))
    assert prev == date(2026, 5, 25)
    assert future == [date(2027, 5, 25), date(2028, 5, 25)]


def test_settlement_skips_weekend():
    assert add_business_days(date(2026, 9, 25), 2) == date(2026, 9, 29)  # vendredi -> mardi
