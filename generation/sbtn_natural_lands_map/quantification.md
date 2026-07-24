# SBTN Natural Lands Map x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure the ground-truth two-row (Natural /
Non-natural) table can verify: hectares of natural land, hectares of
non-natural land, or the natural share of the AOI. No wording names a year;
the map is a fixed 2020 baseline.

Subtype notes:

- `natural_extent`: ask how much natural land the AOI has. The expected
  headline is the Natural row's area_ha.
- `non_natural_extent`: ask how much non-natural (or "not natural") land
  the AOI has. The expected headline is the Non-natural row's area_ha.
- `natural_share`: ask what share/proportion/percentage of the AOI is
  natural land. The expected value is Natural / (Natural + Non-natural)
  area_ha, expressed as a percentage or fraction. This is the one subtype
  where a percentage answer is the point.

Judge expectations (for context, not for the wording): the headline figure
must match ground truth within 5% in any reasonable unit; the answer should
reflect the two-row is_natural grouping (Natural and Non-natural, summed
area_ha); a caveat that the map represents 2020 and is known to
overestimate the extent of natural lands is correct and must not be
penalised.
