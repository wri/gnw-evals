# Deforestation (sLUC) emission factors by agricultural crop: shared prompt-wording rules (all intents)

These rules come from the dataset catalog
(`project-zeno/src/agent/datasets/catalog/deforestation_sluc_emission_factors_by_agricultural_crop.yml`).
Violating them produces cases that fail for wording reasons rather than agent
defects.

1. **Tabular data only — never ask for a map.** This dataset produces tables,
   not maps. Do NOT ask to "map", "show on a map", "where", or for any spatial
   visualisation; such a request should be refused by the agent and is not a
   valid case here.
2. **Name the crop and the country.** Every prompt states one crop from the
   dataset's 42-crop list (e.g. Soybean, Oil Palm, Cocoa, Arabica Coffee,
   Robusta Coffee, Rice, Maize, Sugarcane, Wheat, Tea, Cotton, Banana) and one
   producer country. Match the crop to a plausible producer (Soybean/Brazil,
   Oil Palm/Indonesia or Malaysia, Cocoa/Côte d'Ivoire or Ghana, Coffee/
   Colombia or Peru, Rice/India).
3. **One quantity per prompt.** Ask for exactly one of: the emission factor
   (tCO2e per tonne of product), total sLUC emissions (tCO2e), or production
   volume (tonnes). Do NOT ask for a chart combining emission factor, total
   emissions and production together.
4. **Units.** Emissions and emission factors are in tCO2e (= MgCO2e); frame
   emissions questions in tCO2e (or "tonnes of CO2-equivalent") and production
   in tonnes.
5. **Gas type.** Total emissions and the emission factor use total CO2e by
   default. When the row names a specific gas (CO2, CH4 or N2O), the prompt
   must ask for that gas explicitly. Production-volume prompts do not mention
   a gas.
6. **Reporting year.** Data covers reporting years 2020-2024, with 2024 the
   default. For a 2024 row you may state the year or leave it implicit (the
   agent defaults to 2024); for any other year (2020-2023) state the reporting
   year explicitly.
7. **One analytics query per prompt.** Exactly one unambiguous request per
   prompt; no compound questions.
8. **Natural tone.** Vary sentence shape between variants of the same row.
   Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters.
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
9. **Country names in prose, not codes.** "Indonesia", never "IDN".
10. **English only this round** (`expected_language=en`).
