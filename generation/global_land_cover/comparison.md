# Global land cover x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things is larger, or how they differ. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth. No wording names a year; the product fixes the
periods (2024 for composition, 2015 to 2024 for change). Two-period
comparisons do not exist for this dataset: there is no time axis to split.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;COD`).
  Ask which has more of the row's class (2024 composition), more
  agricultural land (the combined cropland + cultivated grasslands rule
  applies to both countries), or - where the judge_note says so - more of a
  class-to-class transition (2015 to 2024, `land_cover_classes` in
  `start;end` order). Both countries must appear in the prompt.
- `two_class`: one country, two classes named in `land_cover_classes`. Ask
  which class covers more area there today. Both classes must be named
  explicitly; for cropland vs cultivated grasslands the explicit naming is
  exactly what switches the agriculture-combining rule off, so do not
  paraphrase either class as "agriculture".

Judge expectations (for context, not for the wording): direction must be
correct; cited figures within 5%; figure-free but directionally correct
answers pass with unquantified=true.
