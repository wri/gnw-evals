# Tree cover x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure that the ground-truth table can verify:
hectares of tree cover (or, with the context layer, primary forest) in the
fixed 2000 snapshot. No wording names a year, and no wording asks for a
percentage: the value under test is always area_ha.

Subtype notes:

- `cover_area`: ask how much tree cover the AOI has. Blank `canopy_cover`
  means the default 30% threshold, unstated in the prompt. The expected
  headline is the tree cover area_ha total. Say "tree cover", never
  "forest".
- `canopy_threshold`: name the row's threshold explicitly ("at a 50% canopy
  density threshold"). The question is otherwise a plain cover_area ask.
- `primary_forest_area`: ask about primary forest explicitly (the
  `forest_filter=primary_forest` rows); "forest" is legitimate here and
  only here.

Judge expectations (for context, not for the wording): the headline figure
must match ground truth within 5%, reported as an area in hectares or an
honest unit conversion, never as a percentage; the pipeline excludes
tree cover area = 0 rows and the agent is expected to say so, which must
not be penalised.
