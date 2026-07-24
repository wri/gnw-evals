# sLUC crop emission factors x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things is larger, or how they differ. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` names both countries and `crop_types`
  names the single crop. Ask which country has the larger emission factor (or
  total emissions) for that crop; check the judge_note for which column. Both
  countries must appear in the prompt.
- `two_crop`: one country, two crops (the row's `crop_types` lists both). Ask
  which crop has the larger emission factor (or emissions) in that country.
  Both crops must appear in the prompt.
- `two_period`: one crop in one country; the reporting-year window splits into
  two sub-periods that exactly tile it. Name both sub-periods explicitly and
  check the judge_note for the split and the compared column.

Judge expectations: direction must be correct; cited figures within a
reasonable tolerance; tabular framing; reporting year 2024 unless the prompt
states another.
