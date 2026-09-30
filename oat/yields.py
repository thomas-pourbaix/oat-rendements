# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

"""Yield to maturity of an OAT.

OAT market conventions:
- annual coupon, paid every year on the maturity anniversary date;
- accrued interest on an actual/actual basis (ACT/ACT ICMA);
- quoted clean price, in % of face value;
- settlement two business days after trade (T+2).

The yield is the rate r such that:
    dirty price = sum of future cash flows discounted at (1 + r) ** t,
t being expressed in coupon periods (years) under ACT/ACT ICMA.
"""

from datetime import date, timedelta


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _anniversary(maturity: date, year: int) -> date:
    try:
        return maturity.replace(year=year)
    except ValueError:  # 29 February
        return maturity.replace(year=year, day=28)


def coupon_dates(settlement: date, maturity: date) -> tuple[date, list[date]]:
    """Date of the last paid coupon and list of future coupon dates."""
    future = []
    y = maturity.year
    d = maturity
    while d > settlement:
        future.append(d)
        y -= 1
        d = _anniversary(maturity, y)
    return d, future[::-1]


def accrued_interest(coupon: float, settlement: date, maturity: date) -> float:
    prev, future = coupon_dates(settlement, maturity)
    nxt = future[0]
    return coupon * (settlement - prev).days / (nxt - prev).days


def dirty_price(rate: float, coupon: float, settlement: date, maturity: date) -> float:
    prev, future = coupon_dates(settlement, maturity)
    frac = (future[0] - settlement).days / (future[0] - prev).days
    total = 0.0
    for i, _ in enumerate(future):
        cash = coupon + (100.0 if i == len(future) - 1 else 0.0)
        total += cash / (1 + rate) ** (frac + i)
    return total


def yield_to_maturity(clean_price: float, coupon: float, settlement: date, maturity: date) -> float:
    """Annual yield to maturity (0.031 = 3.1 %) when buying at the given clean price."""
    if maturity <= settlement:
        raise ValueError("bond has matured")
    target = clean_price + accrued_interest(coupon, settlement, maturity)
    lo, hi = -0.99, 10.0  # dirty price decreases with the rate: bisection
    for _ in range(200):
        mid = (lo + hi) / 2
        if dirty_price(mid, coupon, settlement, maturity) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2
