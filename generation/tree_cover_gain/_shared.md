# Tree cover gain: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/tree_cover_gain.yml`). Violating
them produces cases that fail for wording reasons rather than agent defects.

1. **Say "tree cover gain", never "restoration".** The catalog forbids the
   term "restoration": gain is a change in tree height from under 5m to over
   5m and includes plantation cycles, natural regrowth and land abandonment,
   not ecological restoration. Do not say "afforestation" or "reforestation"
   either. A prompt may allude to recovery/regrowth in plain terms, but the
   analytics request is always "tree cover gain".
2. **Only the four fixed cumulative periods exist.** Tree cover gain is a
   cumulative layer with exactly four windows: 2000-2020, 2005-2020,
   2010-2020 and 2015-2020. Every prompt must name one of these exact
   windows (the full "since 2000" / "2000 to 2020" period, or one of the
   three shorter cumulative windows ending in 2020). No other start year is
   valid.
3. **Never decompose a period.** Do NOT ask for gain "between 2005 and 2010"
   or any sub-interval; the product reports cumulative totals to 2020 only.
   Sub-period arithmetic is out of scope this round.
4. **Never ask for net change.** Do NOT ask to subtract loss from gain or for
   "net gain/loss" or "net change" - gain and tree cover loss use different
   methodologies and cannot be combined. This round does not author
   net-change prompts (they belong to a refusal cell); wording must never
   imply combining the two datasets.
5. **No canopy threshold.** Tree cover gain takes no canopy parameter - never
   mention a canopy density threshold.
6. **No context layers.** There is no primary/intact forest filter - never
   mention forest-type filters.
7. **Units are hectares.** Any volunteered figure is an area in ha.
8. **Dates are explicit and unambiguous.** Name the cumulative window
   endpoints ("cumulative gain from 2010 to 2020"). No relative expressions.
9. **One analytics query per prompt.** Exactly one unambiguous request (the
   manifest row's period and AOI). No compound questions.
10. **Natural tone.** Wordings should read like a real user: researchers,
    journalists, policy staff. Vary sentence shape between variants of the
    same row. Phrasing styles:
    - `direct`: plain analytical question.
    - `conversational`: first-person, informal framing, still precise on the
      period and AOI.
    - `imprecise`: casual or slightly clumsy wording, but the cumulative
      period and AOI are still stated (hedges and filler allowed).
11. **Country names in prose, not codes.** "the Democratic Republic of the
    Congo", never "COD".
12. **English only this round** (`expected_language=en`).
13. **The x-axis uses the raw cumulative period label** (e.g. "2005-2020"),
    never decomposed 5-year buckets.
