# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end tests of the page (site/), run in a real browser on the data set of conftest.py."""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def page_2y(page: Page, site_url):
    """Page open on a 2-year horizon, ± 1 year window (the default window)."""
    page.goto(site_url)
    page.locator("#n").fill("2")
    expect(page.locator("#n-out")).to_have_text("2")
    return page


def shown_isins(page: Page) -> set[str]:
    return set(page.locator("#table tbody button.isin").all_inner_texts())


class TestShownBondsMatchTheHorizonWindowAndKinds:
    """INV-007: the table shows exactly the bonds of a checked kind whose remaining life is within the window around the horizon."""

    def test_window_and_default_kinds(self, page_2y):
        page_2y.locator("#fresh").uncheck()
        assert shown_isins(page_2y) == {"FR0000000001", "FR0000000002", "FR0000000004", "FR0000000005"}, \
            "INV-007: only nominal bonds with |years - 2| <= 1"

    def test_checking_a_kind_adds_its_bonds(self, page_2y):
        page_2y.locator("#fresh").uncheck()
        page_2y.locator("input[name=kind][value=inflation_euro]").check()
        assert "FR0000000006" in shown_isins(page_2y), "INV-007: a checked kind is shown"


class TestFreshFilterHidesOldOrMissingQuotes:
    """INV-008: with the freshness filter on, no bond whose last trade is older than 30 days, or unknown, is shown."""

    def test_fresh_filter(self, page_2y):
        expect(page_2y.locator("#fresh")).to_be_checked()
        shown = shown_isins(page_2y)
        assert "FR0000000004" not in shown, "INV-008: a 45-day-old quote is hidden"
        assert "FR0000000005" not in shown, "INV-008: a bond never traded is hidden"
        assert shown == {"FR0000000001", "FR0000000002"}, "INV-008: fresh quotes stay shown"


class TestBestYieldIsTheHighestShown:
    """INV-009: the best yield announced and highlighted is the highest yield among the shown bonds."""

    def test_best_yield(self, page_2y):
        expect(page_2y.locator("#summary")).to_contain_text("3,60 %")
        expect(page_2y.locator("tr.best button.isin")).to_have_text("FR0000000002")


class TestClickingAnIsinCopiesIt:
    """INV-010: clicking a bond's ISIN puts exactly that ISIN in the clipboard, then the ISIN is shown again."""

    def test_copy_isin(self, page_2y):
        button = page_2y.locator('button.isin[data-isin="FR0000000002"]')
        button.click()
        expect(button).to_have_text("ISIN copié ✓")
        assert page_2y.evaluate("navigator.clipboard.readText()") == "FR0000000002", "INV-010: clipboard holds the ISIN"
        expect(button).to_have_text("FR0000000002", timeout=3000)


@pytest.mark.parametrize("price, coupon, settlement, maturity", [
    (80.0, 0.0, "2026-11-25", "2031-11-25"),     # zero coupon, whole years
    (100.0, 3.0, "2026-05-25", "2033-05-25"),    # par bond on a coupon date
    (96.25, 2.4, "2026-10-02", "2029-09-24"),    # between two coupons
    (104.8, 5.5, "2026-10-02", "2029-04-25"),    # above par
    (97.0, 1.75, "2026-10-02", "2028-02-29"),    # maturity on 29 February
])
class TestBrowserYieldMatchesPython:
    """INV-011: the browser's yield computation (site/yields.js) gives the same results as oat/yields.py."""

    def test_same_yield(self, page: Page, site_url, price, coupon, settlement, maturity):
        from datetime import date

        from oat.yields import accrued_interest, yield_to_maturity
        page.goto(site_url)
        js = page.evaluate("([p, c, s, m]) => [Yields.yieldToMaturity(p, c, s, m), Yields.accruedInterest(c, s, m)]",
                           [price, coupon, settlement, maturity])
        s, m = date.fromisoformat(settlement), date.fromisoformat(maturity)
        assert js[0] == pytest.approx(yield_to_maturity(price, coupon, s, m), abs=1e-10), "INV-011: same yield"
        assert js[1] == pytest.approx(accrued_interest(coupon, s, m), abs=1e-12), "INV-011: same accrued interest"

    def test_same_settlement(self, page: Page, site_url, price, coupon, settlement, maturity):
        from datetime import date

        from oat.yields import add_business_days
        page.goto(site_url)
        js = page.evaluate("(s) => Yields.addBusinessDays(s, 2)", settlement)
        assert js == add_business_days(date.fromisoformat(settlement), 2).isoformat(), "INV-011: same T+2 settlement"


@pytest.fixture
def calc(page: Page, site_url):
    """Page open on the calculator tab."""
    page.goto(site_url + "#calcul")
    expect(page.locator("#panel-calc")).to_be_visible()
    return page


class TestCalculatorGivesTheYieldAtTheUserPrice:
    """INV-012: for a listed ISIN and a price typed by the user, the calculator shows the yield to maturity at that price, settled at T+2 from today."""

    def test_yield_at_user_price(self, calc):
        from datetime import date

        from oat.yields import add_business_days, yield_to_maturity
        from tests.conftest import BONDS
        bond = next(b for b in BONDS if b["isin"] == "FR0000000002")
        calc.locator("#calc-isin").fill(" fr0000000002 ")   # pasted with spaces, lower case
        calc.locator("#calc-price").fill("97,5")             # French decimal comma
        settlement = add_business_days(date.today(), 2)
        expected = yield_to_maturity(97.5, bond["coupon"], settlement, date.fromisoformat(bond["maturity"]))
        shown = f"{expected * 100:.2f}".replace(".", ",") + " %"
        expect(calc.locator("#calc-ytm")).to_have_text(shown)


class TestCalculatorNeverShowsAYieldWithoutValidInput:
    """INV-013: the calculator shows no yield for an invalid or unlisted ISIN, or a missing or invalid price: it explains what is missing instead."""

    @pytest.mark.parametrize("isin, price, message", [
        ("FR00000", "97", "ISIN incomplet"),
        ("DE0001102580", "97", "ne figure pas"),
        ("FR0000000002", "", "Saisissez votre cours"),
        ("FR0000000002", "abc", "Cours invalide"),
        ("FR0000000002", "0", "Cours invalide"),
    ])
    def test_no_yield(self, calc, isin, price, message):
        calc.locator("#calc-isin").fill(isin)
        calc.locator("#calc-price").fill(price)
        expect(calc.locator("#calc-result")).to_contain_text(message)
        expect(calc.locator("#calc-ytm")).to_have_count(0)

    @pytest.mark.parametrize("fee", ["abc", "-1", "100"])
    def test_no_yield_with_invalid_fee(self, calc, fee):
        calc.locator("#calc-isin").fill("FR0000000002")
        calc.locator("#calc-price").fill("97")
        calc.locator("#calc-fee").fill(fee)
        message = "Frais invalides"
        expect(calc.locator("#calc-result")).to_contain_text(message)
        expect(calc.locator("#calc-ytm")).to_have_count(0)


def _fr(x: float, decimals: int = 2) -> str:
    """French number formatting, as the page writes it (non-breaking space as thousands separator)."""
    return f"{x:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")


class TestNetYieldIncludesTheFees:
    """INV-014: with brokerage fees typed, the net yield is the yield of a bond bought at the total cost, fees charged on the dirty price."""

    def test_net_yield(self, calc):
        from datetime import date

        from oat.yields import accrued_interest, add_business_days, yield_to_maturity
        from tests.conftest import BONDS
        bond = next(b for b in BONDS if b["isin"] == "FR0000000002")
        calc.locator("#calc-isin").fill("FR0000000002")
        calc.locator("#calc-price").fill("97,5")
        calc.locator("#calc-fee").fill("0,2")
        settlement, maturity = add_business_days(date.today(), 2), date.fromisoformat(bond["maturity"])
        accrued = accrued_interest(bond["coupon"], settlement, maturity)
        cost = (97.5 + accrued) * 1.002
        net = yield_to_maturity(cost - accrued, bond["coupon"], settlement, maturity)
        expect(calc.locator("#calc-net")).to_have_text(_fr(net * 100) + " %")
        expect(calc.locator("#calc-unit")).to_have_text(_fr(cost / 100, 4))

    def test_total_cost_matches_a_real_broker_statement(self, page: Page, site_url):
        # External oracle: CIC order of 30/09/2026, OAT 0.75 % 25/11/2028 at 94.4 %, 0.2 % fees,
        # unit cost price shown by the broker (truncated to 4 decimals): 0.9522
        import math
        page.goto(site_url)
        cost = page.evaluate("Yields.totalCost(94.4, 0.002, 0.75, '2026-10-02', '2028-11-25')")
        assert math.floor(cost / 100 * 1e4) / 1e4 == 0.9522, "INV-014: total cost matches the broker's unit cost price"
        # The broker figure is too coarse to tell where fees apply (0.51 EUR on this order): pin it exactly
        from datetime import date

        from oat.yields import accrued_interest
        accrued = accrued_interest(0.75, date(2026, 10, 2), date(2028, 11, 25))
        assert cost == pytest.approx((94.4 + accrued) * 1.002, abs=1e-9), "INV-014: fees are charged on the dirty price"


class TestExplainerExampleMatchesTheCode:
    """INV-015: every figure of the worked example on comprendre.html is what the yield code computes for that order."""

    FACE, PRICE, FEE, COUPON = 40000, 94.4, 0.002, 0.75

    def test_purchase_and_hold(self, page: Page, site_url):
        from datetime import date

        from oat.yields import accrued_interest, yield_to_maturity
        page.goto(site_url + "comprendre.html")
        text = page.locator("main").inner_text()
        settle, mat = date(2026, 10, 2), date(2028, 11, 25)
        acc = accrued_interest(self.COUPON, settle, mat)
        dirty = self.FACE * (self.PRICE + acc) / 100
        total = dirty * (1 + self.FEE)
        coupon = self.FACE * self.COUPON / 100
        expected = {
            "accrued": _fr(self.FACE * acc / 100) + " €",
            "dirty": _fr(dirty) + " €",
            "fees": _fr(dirty * self.FEE) + " €",
            "total": _fr(total) + " €",
            "gain": "+" + _fr(3 * coupon + self.FACE - total) + " €",
            "gross yield": _fr(yield_to_maturity(self.PRICE, self.COUPON, settle, mat) * 100) + " %",
            "net yield": _fr(yield_to_maturity(total / self.FACE * 100 - acc, self.COUPON, settle, mat) * 100) + " %",
        }
        for name, value in expected.items():
            assert value in text, f"INV-015: {name} should read {value!r} on the explainer page"

    def test_sale_before_maturity(self, page: Page, site_url):
        from datetime import date

        from oat.yields import accrued_interest, dirty_price
        page.goto(site_url + "comprendre.html")
        text = page.locator("main").inner_text()
        buy, sell, mat = date(2026, 10, 2), date(2027, 10, 4), date(2028, 11, 25)
        total = self.FACE * (self.PRICE + accrued_interest(self.COUPON, buy, mat)) / 100 * (1 + self.FEE)
        acc = accrued_interest(self.COUPON, sell, mat)
        assert _fr(self.FACE * acc / 100) + " €" in text, "INV-015: accrued interest at sale"
        for rate in (0.025, 0.035, 0.045):
            clean = dirty_price(rate, self.COUPON, sell, mat) - acc
            received = self.FACE * (clean + acc) / 100 * (1 - self.FEE)
            result = received + self.FACE * self.COUPON / 100 - total
            for value in (_fr(clean) + " %", _fr(received) + " €", "+" + _fr(result) + " €"):
                assert value in text, f"INV-015: sale at {rate:.1%} should show {value!r}"
