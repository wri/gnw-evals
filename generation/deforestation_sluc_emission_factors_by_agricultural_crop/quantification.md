# sLUC crop emission factors x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure the ground-truth table can verify, for
one crop in one country and one reporting year.

Subtype notes:

- `emission_factor`: ask for the sLUC emission factor — GHG emissions per
  tonne of product (tCO2e per tonne). Expected column:
  `emission_factor_tCO2e_per_tonne_production`.
- `crop_emissions`: ask for total sLUC emissions (tCO2e) for the crop.
  Expected column: `emissions_tCO2e` (the linearly discounted total). When the
  row names a specific gas (CO2/CH4/N2O), the figure is that gas's share.
- `production`: ask for the crop production volume (tonnes). Expected column:
  `production_tonnes`. No gas is mentioned.

Judge expectations (for context, not for the wording): the headline must match
the named column within a reasonable tolerance; units correct (tCO2e per
tonne, tCO2e, or tonnes); tCO2e = MgCO2e; the reporting year is 2024 unless the
prompt states another.
