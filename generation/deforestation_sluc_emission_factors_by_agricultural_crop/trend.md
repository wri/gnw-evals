# sLUC crop emission factors x trend

Read `_shared.md` first; those rules always apply.

The prompt asks how a crop's figure evolved across the reporting years
2020-2024 (a short annual series). The verifiable core is the direction;
volunteered peak years or endpoint figures must match.

Subtype notes:

- `direction`: ask whether the emission factor, total emissions or production
  rose or fell across the reporting years; check the judge_note for which
  column.
- `peak_year`: ask which reporting year (within the row's window) had the
  highest value of the named column.
- `change_over_period`: ask how the named column at the end of the window
  compares with the start (e.g. 2024 versus 2020).

State the reporting-year range (2020-2024, or the row's range) explicitly.

Judge expectations: direction correct across the reporting years; volunteered
figures must match; tabular framing; figure-free but directionally correct
answers pass with unquantified=true.
