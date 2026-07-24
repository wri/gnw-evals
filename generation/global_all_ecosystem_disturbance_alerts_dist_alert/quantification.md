# DIST-ALERT x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure (or a small set of figures) that the
ground-truth table can verify: hectares of disturbed area over the row's
window, always requested as a breakdown by the row's context layer (the
breakdown is what makes DIST-ALERT the right dataset).

Subtype notes:

- `by_driver`: ask how much disturbed area each likely cause / driver
  accounts for over the window (LDACS driver breakdown). The headline is
  disturbed area (`area_ha`) attributed by driver.
- `by_natural_lands`: ask how much disturbance fell within natural forests
  / natural land classes over the window.
- `by_grasslands`: ask how much disturbance affected natural grasslands,
  shrublands and savannas over the window.
- `by_land_cover`: ask how much disturbed area fell in a land-cover class
  (or broken down by land-cover class) over the window.

Judge expectations (context, not wording): the headline figure is
`area_ha` for the requested breakdown and must match ground truth within a
reasonable tolerance in hectares. For `by_driver` rows whose window reaches
into the most recent ~90 days, LDACS classification is unavailable for that
tail, so a caveat or an omitted-recent-period note is expected and must not
be penalised (see the row's `judge_note`). A figure-free but correct
description passes only where the row's `judge_note` permits it.
