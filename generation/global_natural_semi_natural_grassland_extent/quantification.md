# Natural/semi-natural grassland extent x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure (or a small pair) the ground-truth table
can verify: the grassland area in a year, or the area gained/lost over a
period.

Subtype notes:

- `single_year`: ask for the natural/semi-natural grassland extent (area, in
  hectares) in the row's year. The expected headline is the area_ha total.
- `multi_year_total`: ask how much grassland was lost (or gained) over the
  row's range. The expected headline is the sum of the annual loss (or gain)
  column across the window; check the judge_note for which. Exclude years
  where area is 0 or missing.
- `gain_loss`: ask for both the area gained and the area lost in the row's
  year. Both figures are checked.

Judge expectations (for context, not for the wording): the headline figure
must match ground truth within a reasonable tolerance in sensible units;
zero/missing years are excluded; gains are not treated as restoration nor
losses as necessarily permanent conversion.
