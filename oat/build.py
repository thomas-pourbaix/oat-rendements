"""Build site/data/oats.json: every listed OAT and its yield to maturity.

Usage: python -m oat.build [--out site/data/oats.json]
"""

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from . import euronext, figi
from .yields import accrued_interest, add_business_days, yield_to_maturity


STRIP_NAME = re.compile(r"IPMT|PPMT|ZC|DEM\b|CAC\b")


def _coupon_from_name(name: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", name)
    return float(m.group(1).replace(",", ".")) if m else None


def build(today: date) -> dict:
    settlement = add_business_days(today, 2)
    quotes = [q for q in euronext.fetch_french_govt_quotes() if q.maturity > settlement]
    specs = figi.describe([q.isin for q in quotes])

    bonds = []
    for q in quotes:
        spec = specs.get(q.isin, {})
        coupon = spec.get("coupon")
        if coupon is None:
            coupon = _coupon_from_name(q.name)
        if coupon is None:
            continue
        kind = spec.get("kind", "nominal")
        if STRIP_NAME.search(q.name):  # stripped bonds: coupons (IPMT) or principal (PPMT)
            kind = "strip"
        ytm = yield_to_maturity(q.last_price, coupon, settlement, q.maturity)
        bonds.append({
            "isin": q.isin,
            "name": q.name,
            "ticker": spec.get("ticker"),
            "kind": kind,
            "coupon": coupon,
            "maturity": q.maturity.isoformat(),
            "years": round((q.maturity - settlement).days / 365.25, 3),
            "price": q.last_price,
            "accrued": round(accrued_interest(coupon, settlement, q.maturity), 4),
            "last_trade": q.last_trade.isoformat() if q.last_trade else None,
            "ytm": round(ytm, 6),
            "url": q.url,
        })
    bonds.sort(key=lambda b: b["maturity"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settlement": settlement.isoformat(),
        "count": len(bonds),
        "bonds": bonds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="site/data/oats.json")
    args = parser.parse_args()
    data = build(date.today())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"{data['count']} bonds written to {out}")


if __name__ == "__main__":
    main()
