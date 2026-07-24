# TCL by dominant driver: shared prompt-wording rules (all intents)

These rules exist because of the agent's catalog defaults
(`project-zeno/src/agent/datasets/catalog/tree_cover_loss_by_dominant_driver.yml`).
Violating them produces cases that fail for wording reasons rather than agent
defects.

1. **This is a whole-record aggregate, never a time series.** The dataset
   gives the dominant driver of tree cover loss over the entire 2001-2025
   period as a single aggregate. Do NOT ask for a specific year, a date
   range, or a trend over time - such a question must use Tree cover loss
   instead. Every prompt is about the driver breakdown over the whole record;
   frame it as "since 2001", "over the full 2001-2025 record", "overall", or
   leave the period implicit. Never name a sub-window.
2. **Say "tree cover loss", not "deforestation".** Tree cover includes
   plantations as well as natural forest, so the raw loss is not
   automatically deforestation. The only exception is the named grouping
   "drivers of deforestation" (rule 4), which may be used when that grouping
   is explicitly the subject.
3. **Seven driver classes, exclude Unknown.** Permanent agriculture, Hard
   commodities, Shifting cultivation, Logging, Wildfire, Settlements and
   infrastructure, Other natural disturbances. (An Unknown class exists but
   is excluded from analysis.)
4. **Groupings** (use only when the row's `notes` calls for one):
   - Drivers of deforestation = permanent agriculture + hard commodities +
     settlements and infrastructure.
   - Temporary disturbances = shifting cultivation + logging + wildfire +
     other natural disturbances.
   - All agriculture = permanent agriculture + shifting cultivation.
5. **Canopy threshold.** The default is 30% and legal alternatives are 10,
   15, 20, 25, 50 and 75. Rows at 30 (blank `canopy_cover`) must NOT mention
   a threshold; rows at another value must name it explicitly ("at a 50%
   canopy density threshold").
6. **Presentation is a pie chart or table.** Context for the judge, not a
   wording constraint - do not instruct the chart in the prompt.
7. **One analytics query per prompt.** Exactly one unambiguous request (the
   row's AOI, canopy, and driver/grouping focus). No compound questions.
8. **Natural tone.** Wordings should read like a real user: researchers,
   journalists, policy staff. Vary sentence shape between variants. Phrasing
   styles:
   - `direct`: plain analytical question.
   - `conversational`: first-person, informal framing, still precise.
   - `imprecise`: casual or slightly clumsy wording, parameters still stated.
9. **Country names in prose, not codes.** "Indonesia", never "IDN".
10. **English only this round** (`expected_language=en`).
