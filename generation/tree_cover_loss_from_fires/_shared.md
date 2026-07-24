# Tree cover loss due to fires: shared prompt-wording rules (all intents)

These rules come from the dataset catalog
(`project-zeno/src/agent/datasets/catalog/tree_cover_loss_from_fires.yml`) and
mirror the tree cover loss discipline. Violating them produces cases that fail
for wording reasons rather than agent defects.

1. **Every prompt must signal fire.** This dataset splits annual tree cover
   loss into fire-driven and non-fire loss. The wording must make fire the
   subject — "tree cover loss due to fires", "how much loss was caused by
   fires", "fire-driven tree cover loss" — so the agent picks this dataset
   rather than plain tree cover loss. (The fire intersection is injected by
   the tooling; the manifest leaves `intersections` blank.)
2. **Never ask for carbon emissions.** This dataset does not provide carbon
   emissions. Do NOT ask for CO2/GHG/carbon from the loss; ask about area
   (hectares) only.
3. **Terminology picks the layer.** Plain-canopy rows (no `forest_filter`)
   must say "tree cover loss" and must NOT say "deforestation" or "forest
   loss" alone: the catalog defaults general deforestation/forest-loss
   requests to the primary-forest context layer within its extent. Plain rows
   must also opt out explicitly with a phrase like "across all forest types",
   "including plantations" or "all tree cover".
4. **Primary/intact rows are explicit.** Rows with
   `forest_filter=primary_forest` say "primary forest"; rows with
   `forest_filter=intact_forest` say "intact forest". With a forest layer
   applied, "deforestation" terminology is acceptable.
5. **Thresholds.** Rows at canopy 30 do not mention a threshold (30 is the
   product default on both sides). Rows with any other canopy value must name
   it explicitly ("at a 75% canopy density threshold").
6. **Dates are explicit and unambiguous.** Annual coverage is 2001-2025.
   Single years name the year; ranges name both endpoints. No relative
   expressions this round. Data is annual only — never ask for a seasonal or
   intra-year breakdown.
7. **One analytics query per prompt.** Exactly one unambiguous request per
   prompt; no compound questions.
8. **Natural tone.** Vary sentence shape between variants of the same row.
   Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters.
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
9. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
10. **English only this round** (`expected_language=en`).
