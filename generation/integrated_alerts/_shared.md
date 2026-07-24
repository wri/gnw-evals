# Integrated alerts: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults and selection
hints for the Integrated alerts dataset
(`project-zeno/src/agent/datasets/catalog/integrated_alerts.yml`).
Violating them produces cases that fail for wording reasons rather than
agent defects. The dataset is `integrated_alerts` (near-real-time
integrated disturbance alerts combining DIST-ALERT, GLAD-L, GLAD-S2 and
RADD, 10m, from 1 December 2023 to present).

1. **Keep the query plain; that is what picks this dataset.** Integrated
   alerts is the DEFAULT for a plain recent-disturbance / clearing /
   deforestation-alert query over a whole area. Every prompt MUST be plain:
   ask about recent disturbance (or clearing / deforestation alerts) for
   the AOI and window, with NO ecosystem, class or driver breakdown. Any
   request to break results down by driver, land cover, natural lands or
   grasslands would make the agent correctly pick DIST-ALERT instead, so it
   is a broken case here.
2. **No intersections, ever.** This dataset has no context layers and takes
   no intersections. Never ask for a driver / land-cover / natural-lands /
   grasslands split. The only categorical dimension is the confidence tier
   (low / high / highest), which is intrinsic to the data. A prompt may
   ask for the split by confidence level, but must not ask the agent to
   "set" or "choose" a confidence level, and must not introduce any other
   breakdown.
3. **Alerts, not confirmed outcomes.** Describe the target as "disturbance
   alerts", "clearing" or "deforestation alerts", and treat them as
   indicators of potential disturbance, not confirmed deforestation.
4. **Dates are explicit full dates, never a bare year.** Single points say
   the month and year ("in May 2024"); ranges say both endpoints ("from
   January to December 2024"). Where a row uses a relative expression
   ("over the last three months"), the resolved window is fixed by the
   manifest's `start_date`/`end_date`; use relative wording sparingly and
   prefer absolute forms. Never phrase a year on its own (this is an alert
   stream, not an annual product).
5. **Units are hectares.** Ask for disturbed/alert area in hectares; never
   pixels, counts or square kilometres as the headline unit.
6. **Do not set thresholds or filters this dataset lacks.** Integrated
   alerts takes no canopy-cover threshold and no forest-type filter; never
   mention a canopy percentage or a "primary forest" filter.
7. **One analytics query per prompt.** Exactly one unambiguous analytics
   request (the row's AOI and window, optionally split by confidence). No
   compound questions, no second breakdown, no optional extras.
8. **Natural tone.** Wordings should read like a real user (researcher,
   journalist, policy analyst). Vary sentence shape between variants of the
   same row. Phrasing styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise on the
     AOI and window.
   - `imprecise`: casual or slightly clumsy wording, hedges and filler
     allowed, but the AOI and dates are still stated.
9. **Country names in prose, not codes.** "the Democratic Republic of the
   Congo", never "COD".
10. **English only this round** (`expected_language=en`).
11. **Chart and caveat facts are scoring context, not wording.** That
    totals / a confidence breakdown render as a pie and trends render as a
    line (x = alert month, one line per confidence tier), that "highest"
    confidence may be absent, and the alert-system/confidence caveats, all
    belong to the judge (see the per-intent `judge_note`s). Do NOT quote a
    chart type or caveat into the prompt.
