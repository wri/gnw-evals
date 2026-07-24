# Integrated alerts x trend

Read `_shared.md` first; those rules always apply.

The prompt asks how alert area evolved over the row's window, for the whole
AOI with no ecosystem or driver breakdown. The verifiable core is the
direction (rising, falling, flat, reversal) of monthly disturbed area;
volunteered peak months, endpoints or percentage changes must match the
series.

Subtype notes:

- `direction`: ask whether disturbance alerts are going up or down (or how
  they have developed) across the window.
- `monthly_trend`: ask for the month-by-month pattern of alert area over
  the window (this maps to a line chart of `area_ha` by alert month, one
  line per confidence tier).

Judge expectations (context, not wording): direction must be correct for
the stated window; volunteered figures must match the series. Units are
hectares. The temporal view is expected to render as a line chart, never
bars (scoring context only). Figure-free but directionally correct answers
pass with `unquantified=true` where the row's `judge_note` allows it.
