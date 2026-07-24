# Tree cover loss due to fires x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a figure the ground-truth table can verify: fire-driven
tree cover loss for a year or range. Fire and non-fire loss sum to total
area_ha.

Subtype notes:

- `single_year`: ask how much tree cover loss was due to fires (and, if
  natural, how it compares with non-fire loss) in the row's year. The expected
  headline is `tree_cover_loss_from_fires_area_ha`.
- `multi_year_total`: ask for total fire-driven loss over the row's range (the
  sum of the fires column).
- `canopy_threshold`: name the row's threshold explicitly; otherwise a plain
  fire-loss quantification.
- `primary_forest`: ask about fire-driven loss within primary forest
  explicitly ("deforestation" acceptable here).

Judge expectations (for context, not for the wording): the headline matches
ground truth within a reasonable tolerance in hectares; the fire and non-fire
components sum to total area_ha; never report carbon emissions.
