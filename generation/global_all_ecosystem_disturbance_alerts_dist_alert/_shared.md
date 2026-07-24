# DIST-ALERT: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults and selection
hints for the DIST-ALERT dataset
(`project-zeno/src/agent/datasets/catalog/global_all_ecosystem_disturbance_alerts_dist_alert.yml`).
Violating them produces cases that fail for wording reasons rather than
agent defects. The dataset is
`global_all_ecosystem_disturbance_alerts_dist_alert` (near-real-time
vegetation disturbance alerts, all ecosystems, 30m, from 1 December 2023 to
present).

1. **The breakdown is what picks this dataset.** DIST-ALERT is selected
   ONLY when the user needs disturbance alerts RESTRICTED TO or BROKEN DOWN
   BY a specific ecosystem or class that Integrated Alerts cannot filter.
   Every prompt MUST ask for that breakdown/filter, matching the row's
   `intersections` value: `driver` (likely cause / LDACS attribution),
   `natural_lands` (natural forests / natural land classes),
   `grasslands` (natural grasslands, shrublands, savannas), or `land_cover`
   (a named land-cover class such as tree cover, wetlands or cropland). A
   prompt with no such breakdown would make the agent correctly pick
   Integrated Alerts, so it is a broken case here.
2. **Phrase the breakdown naturally, matching the row's layer.**
   - `driver`: "by likely cause / by driver / what's driving the
     disturbance".
   - `natural_lands`: "within natural forests / across natural land
     classes / natural ecosystems".
   - `grasslands`: "in natural grasslands, shrublands and savannas".
   - `land_cover`: "broken down by land-cover class" or naming one class
     (e.g. "within tree cover", "in wetlands", "on cropland").
3. **Alerts, not confirmed outcomes.** Describe the target as
   "disturbance alerts" or "vegetation disturbance", never "confirmed
   deforestation" or "confirmed conversion". Asking for "disturbance
   alerts broken down by driver" is fine; asking for "how much forest was
   definitely converted" is not.
4. **Dates are explicit full dates, never a bare year.** Single points say
   the month and year ("in July 2024", "during May 2024"); ranges say both
   endpoints ("from January to June 2024", "between March and August
   2024"). Where a row uses a relative expression ("over the last twelve
   months"), the resolved window is fixed by the manifest's
   `start_date`/`end_date`; use relative wording sparingly and prefer
   absolute forms. Never phrase a year on its own (this is an alert stream,
   not an annual product).
5. **Units are hectares.** Ask for disturbed/alert area in hectares; never
   pixels, counts or square kilometres as the headline unit.
6. **Do not set thresholds or filters this dataset lacks.** DIST-ALERT
   takes no canopy-cover threshold and no forest-type filter; never mention
   a canopy percentage or a "primary forest" filter. The two confidence
   levels (low/high) live in the data and are not something the user sets;
   do not ask the agent to "choose" or "set" a confidence level.
7. **One analytics query per prompt.** Exactly one unambiguous analytics
   request (the row's AOI, window and single breakdown). No compound
   questions, no second breakdown, no optional extras.
8. **Natural tone.** Wordings should read like a real user (researcher,
   journalist, policy analyst). Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on the
     AOI, window and breakdown.
   - `imprecise`: casual or slightly clumsy wording, hedges and filler
     allowed, but the AOI, dates and breakdown are still stated.
9. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
10. **English only this round** (`expected_language=en`).
11. **Caveats are scoring context, not wording.** The LDACS quarterly
    update / most-recent-12-months / no-classification-in-the-last-90-days
    caution, the ">=75 days sustained loss for potential conversion" rule,
    and "always interpret alerts as indicators, not definitive outcomes"
    belong to the judge (see the per-intent `judge_note`s). Do NOT quote
    them into the prompt.
