# Integrated alerts x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure (or a small set of figures) that the
ground-truth table can verify: hectares of disturbed/alert area over the
row's window, for the whole AOI with no ecosystem or driver breakdown.

Subtype notes:

- `disturbed_area`: ask how much disturbed / cleared area was flagged by
  the alerts over the window (a single headline total). The expected
  figure is `area_ha` summed over the period.
- `by_confidence`: ask for the alert area split by confidence level
  (low / high / highest) over the window. This is the only categorical
  breakdown this dataset supports; it lives in the data, so the wording
  asks how the total splits across confidence tiers, not for the agent to
  set a tier.

Judge expectations (context, not wording): the headline figure is
`area_ha` and must match ground truth within a reasonable tolerance in
hectares. For `by_confidence` rows the per-tier split must match the
series; the "highest" tier may be absent where only one system covered the
area/time, which is not an error. Totals or a confidence breakdown are
expected to render as a pie chart (scoring context only). A figure-free but
correct description passes only where the row's `judge_note` permits it.
