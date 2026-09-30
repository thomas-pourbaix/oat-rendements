# oat-rendements

## Language

Everything is in English (identifiers, comments, docstrings, tests, README, CHANGELOG, commit
messages) except what the user sees: page labels and texts in `site/` stay in French.

## Git

- Push without asking once the tests pass: no need to wait for Thomas's go-ahead.
- `CHANGELOG.md` (Keep a Changelog): fill in the "Unreleased" section in the same commit as the change.

## Tests

Every test is tied to an invariant of `INVARIANTS.md` (`INV-XXX` in the test class docstring).
Run `python -m pytest -q` before committing.
