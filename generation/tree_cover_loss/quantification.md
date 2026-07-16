# Tree cover loss x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure (or a small set of figures) that the
ground-truth table can verify: hectares of loss for a year or range, or GHG
emissions from that loss.

Subtype notes:

- `single_year` / `multi_year_total`: ask "how much/how many hectares" for
  the row's year(s). The expected headline is the area_ha total.
- `canopy_threshold`: name the row's threshold explicitly. The question is
  otherwise a plain quantification.
- `primary_forest`: ask about primary forest loss explicitly.
- `intact_forest`: ask about intact forest loss explicitly.
- `deforestation_default`: say "deforestation" plainly (this subtype tests
  the catalog's documented primary-forest default); do not add an opt-out.
- `driver_share`: ask what share/amount a named driver contributed (the PoC
  case asks about the dominant driver share for the whole record).
- `fires_split`: ask how much of the loss was fire-driven.
- `emissions`: ask for GHG emissions from tree cover loss (the
  carbon_emissions_MgCO2e column), not area.

Judge expectations (for context, not for the wording): the headline figure
must match ground truth within 5% in any reasonable unit; because the
catalog tells the agent to always report emissions alongside loss,
volunteered emissions figures are checked against the carbon column.
