# Integrated alerts x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things saw more disturbance, or how they
differ, for the whole AOI with no ecosystem or driver breakdown. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth (hectares).

Subtype notes:

- `two_country`: the row's `aoi_ids` holds both countries (e.g. `BRA;IDN`).
  Ask which had more disturbed / cleared area (or to compare them) over the
  row's window. Both countries must appear in the prompt; the same window
  applies to both.
- `two_period`: one country, one window that splits into two compared
  sub-periods. The prompt must name both sub-periods explicitly ("from
  January to June 2024 compared with July to December 2024") and they must
  exactly tile the row's `start_date`-`end_date` window. Check the row's
  `judge_note` for the intended split.

Judge expectations (context, not wording): the comparative direction must
be correct; cited figures within a reasonable hectare tolerance. Near-zero
pairs (e.g. GBR, CRI) keep normal wording; the small magnitudes are the
test. Figure-free but directionally correct answers pass with
`unquantified=true` where the row's `judge_note` allows it.
