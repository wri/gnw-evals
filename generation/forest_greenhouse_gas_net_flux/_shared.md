# Forest GHG net flux: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/forest_greenhouse_gas_net_flux.yml`).
Violating them produces cases that fail for wording reasons rather than agent
defects.

1. **This is a single whole-period total, never a time series.** Net flux is
   one total over the model period 2001-2025 (emissions minus removals). Do
   NOT ask for a trend, a time series, annual values, year-by-year change, or
   any single year. A prompt that asks for change over time forces the wrong
   dataset and is invalid here.
2. **Do not ask to annualise.** Users may divide the total by 25 for an
   average annual figure, but the prompt must not request that division or
   ask for a "per year" value - the request is the raw whole-period total.
3. **Units are MgCO2e** (tonnes of CO2 equivalent). Any volunteered figure is
   in MgCO2e or an honest conversion.
4. **Net sink vs net source.** Net-negative flux (removals exceed emissions)
   is a "net sink"; net-positive flux (emissions exceed removals) is a "net
   source". Prompts may ask which the country's forests are.
5. **Presentation is a split bar.** Emissions on the positive y-axis,
   removals on the negative. This is context for the judge, not a wording
   constraint - do not instruct the chart in the prompt.
6. **Canopy threshold.** The default is 30% and the only legal alternatives
   are 50% and 75%. Rows at 30 (blank `canopy_cover`) must NOT mention a
   threshold; rows at 50 or 75 must name it explicitly ("at a 50% canopy
   density threshold"). No other value is valid.
7. **Do not state dates.** The dataset is fixed to 2001-2025; naming a year
   or a range would push the request to another dataset. Frame the period as
   "over the full period", "since 2001", "the whole 2001-2025 record", or
   leave it implicit - never a sub-window.
8. **No context layers.** There is no forest-type (primary/intact) filter -
   never mention one.
9. **One analytics query per prompt.** Exactly one unambiguous request (the
   manifest row's AOI and canopy). No compound questions.
10. **Natural tone.** Wordings should read like a real user: researchers,
    journalists, policy staff. Vary sentence shape between variants. Phrasing
    styles:
    - `direct`: plain analytical question.
    - `conversational`: first-person, informal framing, still precise.
    - `imprecise`: casual or slightly clumsy wording, parameters still stated.
11. **Country names in prose, not codes.** "Colombia", never "COL".
12. **English only this round** (`expected_language=en`).
