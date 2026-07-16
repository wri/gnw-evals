# Tree cover loss: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/tree_cover_loss.yml`). Violating
them produces cases that fail for wording reasons rather than agent defects.

1. **Terminology picks the layer.** Plain-canopy cases (no `forest_filter` in
   the manifest row) must say "tree cover loss" and must NOT say
   "deforestation" or "forest loss" alone: the catalog tells the agent to
   default to the primary-forest context layer for general
   deforestation/forest-loss requests inside its extent. Plain cases must
   also opt out explicitly with a phrase like "across all forest types",
   "including plantations" or "all tree cover".
2. **Primary/intact cases are explicit.** Rows with
   `forest_filter=primary_forest` say "primary forest"; rows with
   `forest_filter=intact_forest` say "intact forest". The
   `deforestation_default` subtype is the deliberate exception: it says
   "deforestation" plainly to test the documented default substitution.
3. **Thresholds.** Rows with canopy 30 do not mention a threshold (30 is the
   product default on both sides). Rows with any other canopy value must name
   it explicitly ("at a 75% canopy density threshold").
4. **Dates are explicit and unambiguous.** Single years say the year; ranges
   say both endpoints ("from 2015 to 2020"). No relative expressions ("last
   five years") in this generation round: expected dates must be derivable
   from the prompt alone.
5. **One analytics query per prompt.** The prompt must map to exactly one
   unambiguous analytics request (the manifest row's parameters). No
   compound questions, no optional extras.
6. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters ("I'm looking into Costa Rica's forests - how much tree
     cover, counting all forest types, was lost there in 2021?").
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
7. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
8. **English only this round** (`expected_language=en`).
