/* Copyright (C) 2026 Thomas Pourbaix
   SPDX-License-Identifier: AGPL-3.0-only */

/* Yield to maturity of an OAT, in the browser.
   Port of oat/yields.py (same conventions: annual coupon on the maturity anniversary,
   ACT/ACT ICMA accrued interest, clean price in % of face value, T+2 settlement).
   Both implementations must agree: see INV-011.
   Dates are "YYYY-MM-DD" strings, handled in UTC to stay clear of time zones. */

const Yields = (() => {
  const DAY = 864e5;
  const toTime = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  const toIso = (t) => new Date(t).toISOString().slice(0, 10);
  const days = (a, b) => Math.round((toTime(a) - toTime(b)) / DAY);

  function addBusinessDays(iso, n) {
    let t = toTime(iso);
    while (n > 0) {
      t += DAY;
      const wd = new Date(t).getUTCDay();
      if (wd !== 0 && wd !== 6) n -= 1;
    }
    return toIso(t);
  }

  function anniversary(maturity, year) {
    const mmdd = maturity.slice(5);
    return `${year}-${mmdd === "02-29" ? "02-28" : mmdd}`;  // 29 February
  }

  // Date of the last paid coupon and list of future coupon dates.
  function couponDates(settlement, maturity) {
    const future = [];
    let y = +maturity.slice(0, 4);
    let d = maturity;
    while (d > settlement) {
      future.push(d);
      y -= 1;
      d = anniversary(maturity, y);
    }
    return [d, future.reverse()];
  }

  function accruedInterest(coupon, settlement, maturity) {
    const [prev, future] = couponDates(settlement, maturity);
    return coupon * days(settlement, prev) / days(future[0], prev);
  }

  function dirtyPrice(rate, coupon, settlement, maturity) {
    const [prev, future] = couponDates(settlement, maturity);
    const frac = days(future[0], settlement) / days(future[0], prev);
    let total = 0;
    future.forEach((_, i) => {
      const cash = coupon + (i === future.length - 1 ? 100 : 0);
      total += cash / Math.pow(1 + rate, frac + i);
    });
    return total;
  }

  // Annual yield to maturity (0.031 = 3.1 %) when buying at the given clean price.
  function yieldToMaturity(cleanPrice, coupon, settlement, maturity) {
    if (maturity <= settlement) throw new Error("bond has matured");
    const target = cleanPrice + accruedInterest(coupon, settlement, maturity);
    let lo = -0.99, hi = 10;  // dirty price decreases with the rate: bisection
    for (let i = 0; i < 200; i++) {
      const mid = (lo + hi) / 2;
      if (dirtyPrice(mid, coupon, settlement, maturity) > target) lo = mid;
      else hi = mid;
      if (hi - lo < 1e-12) break;
    }
    return (lo + hi) / 2;
  }

  return { addBusinessDays, couponDates, accruedInterest, dirtyPrice, yieldToMaturity };
})();
