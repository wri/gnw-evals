# Tree cover: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/tree_cover.yml`). Violating them
produces cases that fail for wording reasons rather than agent defects.

1. **Never state a year or date range.** The product is a single static
   2000 snapshot (content_date_fixed): user-supplied dates are ignored, the
   manifest's `date_expression` is `fixed`, and no date expectation is
   scored. Ask for the extent plainly ("how much tree cover does Brazil
   have?"); do not write "in 2000" or any other date.
2. **Terminology picks the layer.** Plain rows (no `forest_filter` in the
   manifest row) say "tree cover" (or "tree canopy cover") and must NOT say
   "forest": without a context layer the product is tree cover, not forest.
   Rows with `forest_filter=primary_forest` say "primary forest" explicitly;
   that layer is the only case where "forest" is legitimate.
3. **Thresholds.** Rows with a blank `canopy_cover` use the product default
   of 30, which the prompt must not mention. Any other value (50, 75) must
   be named explicitly ("at a 75% canopy density threshold").
4. **Area, not percentage.** Ask for area ("how much", "how many
   hectares of tree cover"), never "what percent of the country is tree
   cover": the value under test is tree cover area_ha, and percentage
   answers fail scoring.
5. **No change or trend questions.** One snapshot only. Change requests
   belong to the Tree Cover Loss and Tree Cover Gain datasets (which the
   catalog recommends by name for change); keep every prompt a snapshot
   question.
6. **One analytics query per prompt.** The prompt must map to exactly one
   unambiguous analytics request (the manifest row's parameters). No
   compound questions, no optional extras.
7. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters ("I'm mapping baselines for a report - how many hectares of
     tree cover does the Democratic Republic of the Congo have?").
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
8. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
9. **English only this round** (`expected_language=en`).
