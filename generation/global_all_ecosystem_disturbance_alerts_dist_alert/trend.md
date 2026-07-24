# DIST-ALERT x trend

Read `_shared.md` first; those rules always apply.

The prompt asks how disturbed area evolved over the row's window, broken
down by the row's context layer. The verifiable core is the direction
(rising, falling, flat, reversal) of monthly disturbed area; volunteered
peak months, endpoints or percentage changes must match the series.

Subtype notes:

- `direction`: ask whether disturbance is going up or down (or how it has
  developed) across the window, for the row's breakdown.
- `monthly_trend`: ask for the month-by-month pattern of disturbed area
  over the window, for the row's breakdown (this maps to a line chart of
  `area_ha` by alert month).

Judge expectations (context, not wording): direction must be correct for
the stated window; volunteered figures must match the series. Units are
hectares. For `driver` breakdowns reaching into the most recent ~90 days,
LDACS classification is unavailable for that tail and a caveat is expected
(see the row's `judge_note`). Figure-free but directionally correct answers
pass with `unquantified=true` where the row's `judge_note` allows it.
