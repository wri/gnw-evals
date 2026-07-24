# Forest GHG net flux x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two countries has the larger net GHG flux (larger
net source, or larger net sink), or how they differ. The verifiable core is
the comparative claim's direction; any volunteered figures (MgCO2e) must
match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;IDN`).
  Ask which country's forests are the larger net source (or which is the
  larger net sink), or to compare their whole-period net flux totals. Both
  countries must appear in the prompt; the whole-period basis applies to
  both. Where a row sets a canopy threshold, it applies to both countries.
- Near-zero / net-sink rows (GBR, CRI): wording is normal; the small
  magnitudes (and possible net-sink sign) are the test - the direction must
  still be correct.

There are no trend or period-split rows: net flux is a single whole-period
total and cannot be split into comparable sub-periods.

Judge expectations: direction must be correct; cited figures within
tolerance; figure-free but directionally correct answers pass. Net
sink/source language must follow each country's sign; no annualising.
