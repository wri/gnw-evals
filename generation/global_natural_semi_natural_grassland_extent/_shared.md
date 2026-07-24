# Natural/semi-natural grassland extent: shared prompt-wording rules (all intents)

These rules come from the dataset catalog
(`project-zeno/src/agent/datasets/catalog/global_natural_semi_natural_grassland_extent.yml`).
Violating them produces cases that fail for wording reasons rather than agent
defects.

1. **Name the ecosystem precisely.** Say "natural/semi-natural grassland"
   (or "natural grassland", "grassland extent"). The dataset covers natural
   and semi-natural grasslands, shrublands and savannas — low vegetation
   under 3 m with at least 30% cover. Do NOT ask about cultivated grasslands,
   croplands, pasture, planted/improved pasture or open shrubland: those
   belong to Global Land Cover, and such wording would select the wrong
   dataset.
2. **No thresholds, no filters.** This dataset takes no canopy-density
   threshold and no context layers. Never mention a canopy percentage or a
   forest-type filter.
3. **Units are hectares.** Area/extent is reported in hectares; ask "how many
   hectares".
4. **Extent is a stock; gains and losses are flows.** An "extent"/"area"
   question asks for the grassland area in a year. A "gain"/"loss" question
   asks how much grassland was gained or lost. Keep a single prompt to one of
   these. When a prompt is about gains, phrase it plainly ("how much grassland
   was gained"); the agent's caveat that gains are not necessarily ecological
   restoration is the judge's business, not the wording's.
5. **Dates are explicit and unambiguous.** Annual coverage is 2000-2022.
   Single years name the year; ranges name both endpoints ("from 2005 to
   2015"). No relative expressions this round.
6. **One analytics query per prompt.** Exactly one unambiguous request per
   prompt; no compound questions, no optional extras.
7. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters.
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
8. **Country names in prose, not codes.** "Bolivia", never "BOL".
9. **English only this round** (`expected_language=en`).
