# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Clicking a bond's ISIN copies it to the clipboard.
- `INVARIANTS.md`: catalogue of the rules the code must always respect, each one tied to its tests.
- `CLAUDE.md`: repository preferences.
- AGPL-3.0: SPDX header in every source file and a link to the source code on the page (AGPL section 13).

### Fixed
- Bonds traded on the day of the build lost their last trade date (Euronext swaps the date and time layout for them), so the 30-day filter hid almost every nominal OAT.
- An intermittent empty page from the Euronext API silently truncated the bond list; it is now retried, and the build fails if it persists.

### Changed
- Code, comments, tests and README are now in English; the page stays in French.
- Bond kinds in `oats.json` renamed: `nominale` → `nominal`, `indexee_euro` → `inflation_euro`, `indexee_france` → `inflation_france`.
