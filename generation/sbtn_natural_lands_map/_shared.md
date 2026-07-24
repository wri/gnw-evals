# SBTN Natural Lands Map: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/sbtn_natural_lands_map.yml`).
Violating them produces cases that fail for wording reasons rather than
agent defects.

1. **Never state a year or date range.** The map is a single static 2020
   baseline (content_date_fixed): user-supplied dates are ignored, the
   manifest's `date_expression` is `fixed`, and no date expectation is
   scored. Ask in the present tense ("how much of Peru is natural land?");
   naming a year only invites the agent to filter on a date the product
   ignores.
2. **Vocabulary.** "Natural land(s)" and "non-natural land" are the
   product's terms. The output always groups by is_natural into exactly two
   rows (Natural / Non-natural), summing area_ha; wordings ask about one
   side of that split, or about the natural share, never for a
   class-by-class breakdown.
3. **No change or trend questions.** One year only. If a wording drifts
   towards change over time it is wrong for this dataset (the catalog
   recommends Global Land Cover by name for change questions); keep every
   prompt a snapshot question.
4. **No protection or legality framing.** The map does not represent
   protection status or legality: never say "protected", "conservation
   areas", "legally designated" or similar, and never imply the natural
   share is the protected share.
5. **Stay above the class level.** The underlying legend includes a
   natural-forest grouping (classes 2, 5, 8, 9) and non-natural tree cover
   (classes 14, 17, 18), but this round's rows are about natural vs
   non-natural land overall; do not ask forest-specific questions.
6. **One analytics query per prompt.** The prompt must map to exactly one
   unambiguous analytics request (the manifest row's parameters). No
   compound questions, no optional extras.
7. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on
     parameters ("I'm scoping a supply-chain assessment - how much of
     Malaysia counts as natural land?").
   - `imprecise`: casual or slightly clumsy wording, but every parameter
     still stated (hedges and filler allowed, parameters not negotiable).
8. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
9. **English only this round** (`expected_language=en`).
