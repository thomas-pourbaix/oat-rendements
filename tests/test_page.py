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
