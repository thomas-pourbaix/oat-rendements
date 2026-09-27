"""Calcul du rendement actuariel à l'échéance d'une OAT.

Conventions du marché des OAT :
- coupon annuel, versé chaque année à la date anniversaire de l'échéance ;
- coupon couru en base exact/exact (ACT/ACT ICMA) ;
- prix coté pied de coupon, en % du nominal ;
- règlement-livraison à J+2 ouvrés.

Le rendement est le taux r tel que :
    prix plein = somme des flux futurs actualisés à (1 + r) ** t,
t étant exprimé en périodes de coupon (années) selon ACT/ACT ICMA.
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
    except ValueError:  # 29 février
        return maturity.replace(year=year, day=28)


def coupon_dates(settlement: date, maturity: date) -> tuple[date, list[date]]:
    """Date du dernier coupon détaché et liste des dates de coupon futures."""
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
    """Taux actuariel annuel (0.031 = 3,1 %) pour un achat au prix pied de coupon donné."""
    if maturity <= settlement:
        raise ValueError("titre échu")
    target = clean_price + accrued_interest(coupon, settlement, maturity)
    lo, hi = -0.99, 10.0  # le prix plein décroît avec le taux : dichotomie
    for _ in range(200):
        mid = (lo + hi) / 2
        if dirty_price(mid, coupon, settlement, maturity) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2
