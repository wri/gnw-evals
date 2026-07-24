# Tree cover gain x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two countries gained more tree cover, or how they
differ. The verifiable core is the comparative claim's direction; any
volunteered figures (ha) must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;IDN`).
  Ask which gained more cumulative tree cover (or to compare) over the row's
  single cumulative period. Both countries must appear in the prompt and the
  one cumulative window applies to both. Never decompose the window.
- Near-zero rows (GBR, CRI): wording is normal; the small magnitudes are the
  test - the direction must still be correct.

There are no `two_period` rows: the four cumulative windows all end in 2020
and overlap, so there is no valid split into two comparable sub-periods.

Judge expectations: direction must be correct; cited figures within
tolerance; figure-free but directionally correct answers pass. The answer
must say "tree cover gain", not "restoration", and must not compute net
change against tree cover loss.
