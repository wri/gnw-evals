# DIST-ALERT x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things saw more disturbance, or how they
differ, always for the row's context-layer breakdown. The verifiable core
is the comparative claim's direction; volunteered figures must match ground
truth (hectares).

Subtype notes:

- `two_country`: the row's `aoi_ids` holds both countries (e.g. `BRA;IDN`).
  Ask which had more disturbed area (or to compare them) over the row's
  window, for the row's breakdown. Both countries must appear in the
  prompt; the same window and the same breakdown apply to both.
- `two_period`: one country, one window that splits into two compared
  sub-periods. The prompt must name both sub-periods explicitly ("from
  January to June 2024 compared with July to December 2024") and they must
  exactly tile the row's `start_date`-`end_date` window. Check the row's
  `judge_note` for the intended split. The breakdown applies to both
  sub-periods.

Judge expectations (context, not wording): the comparative direction must
be correct; cited figures within a reasonable hectare tolerance. For
`driver` breakdowns whose later sub-period or window reaches into the most
recent ~90 days, LDACS classification is unavailable for that tail and the
comparison should carry that caveat (see the row's `judge_note`).
Figure-free but directionally correct answers pass with `unquantified=true`
where the row's `judge_note` allows it.
