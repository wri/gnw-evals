# Tree cover x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two countries has more tree cover (or primary
forest). The verifiable core is the comparative claim's direction;
volunteered figures must match ground truth and must be areas, not
percentages. No wording names a year; the product is the fixed 2000
snapshot. Two-period comparisons do not exist for this dataset: there is
only one snapshot, so `two_country` is the only subtype.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;COD`).
  Ask which has more tree cover, or to compare the two. Both countries must
  appear in the prompt.
- Rows with a non-default `canopy_cover` (50, 75) must name the threshold
  explicitly and it applies to both countries.
- Rows with `forest_filter=primary_forest` compare primary forest
  explicitly ("which has more primary forest"); plain rows say "tree
  cover" and must not say "forest".
- Smaller-magnitude pairs (GBR, CRI): wording is normal; the modest
  magnitudes are the test.

Judge expectations (for context, not for the wording): direction must be
correct; cited figures within 5% and in hectares (or honest conversions),
never percentages; figure-free but directionally correct answers pass with
unquantified=true.
