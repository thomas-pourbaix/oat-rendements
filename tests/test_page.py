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
