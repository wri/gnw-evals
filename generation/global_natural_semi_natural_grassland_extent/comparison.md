# Natural/semi-natural grassland extent x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things is larger, or how they differ. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` names both countries (e.g. `BRA;MEX`).
  Ask which has more grassland (extent), or which lost more grassland over the
  window; check the judge_note for which. Both countries must appear in the
  prompt; the window applies to both.
- `two_period`: one country, one window that splits into the two compared
  periods. The prompt must name both sub-periods explicitly ("2000 to 2011
  compared with 2012 to 2022") and they must exactly tile the row's
  start_year-end_year window. Check the judge_note for the intended split and
  the compared quantity (usually grassland loss).
- Near-zero rows (e.g. Costa Rica): wording is normal; the small magnitudes
  are the test.

Judge expectations: direction must be correct; cited figures within a
reasonable tolerance; figure-free but directionally correct answers pass with
unquantified=true.
