# Global land cover: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/global_land_cover.yml`). Violating
them produces cases that fail for wording reasons rather than agent defects.

1. **Never state a year or date range.** The product fixes its own periods:
   composition questions read the 2024 snapshot, change questions read the
   2015 to 2024 transition. The manifest's `date_expression` is `none` and no
   date expectation is scored. A prompt that names a year invites the agent
   to filter on a date the product ignores. Present tense is the natural
   register for composition ("how much cropland is there in...");
   "changed from X to Y" for change.
2. **Composition vs change is picked by the wording.** `class_area` and
   `agriculture_combined` rows ask what the land cover *is* (one class's
   area, or agriculture generically). `change_area` rows ask how much land
   *changed* from one class to another (or out of a class). Never mix the
   two registers in one prompt.
3. **Anchor to land cover.** Prompts about the "tree cover" class must frame
   the question as land cover ("of Brazil's land, how much is classified as
   tree cover in the latest land cover data?") so they cannot be read as the
   separate Tree Cover (canopy extent) dataset's question.
4. **Never ask for tree cover loss.** "Tree cover loss", "deforestation" and
   "forest loss" belong to the Tree Cover Loss dataset and the catalog
   redirects such requests. Change rows involving tree cover say "changed
   from tree cover to ..." and nothing stronger.
5. **Land cover change, not land use change.** The product shows land cover
   change only; it does not represent conversion. Avoid "converted",
   "conversion" and "land use" in wordings.
6. **Class vocabulary.** Use the product's class names naturally: bare
   ground & sparse vegetation, short vegetation, tree cover, wetlands,
   water, snow/ice, cropland, cultivated grasslands, built-up land. The
   manifest's `land_cover_classes` column records which class(es) a row is
   about; for `change_area` rows the order is `start;end`.
7. **Agriculture rows do not name classes.** `agriculture_combined` rows say
   "agricultural land" / "agriculture" / "farmland" without enumerating
   classes: the documented behaviour under test is the agent combining
   cropland + cultivated grasslands. Rows that explicitly name a single
   class (e.g. cropland) are scored on that class alone.
8. **One analytics query per prompt.** The prompt must map to exactly one
   unambiguous analytics request (the manifest row's parameters). No
   compound questions, no optional extras.
9. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters ("I'm looking at Ghana's farmland - roughly how much of the
     country is agricultural land these days?").
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
10. **Country names in prose, not codes.** "the Democratic Republic of the
    Congo", never "COD".
11. **English only this round** (`expected_language=en`).
