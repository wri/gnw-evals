# Tree cover loss x trend

Read `_shared.md` first; those rules always apply.

The prompt asks how loss evolved over the row's window. The verifiable core
is the direction (rising, falling, flat, reversal); volunteered peak years,
endpoints or percentage changes must match the series.

Subtype notes:

- `direction`: ask whether loss is going up or down (or how it has
  developed) over the window.
- `peak_year`: ask which year had the highest loss in the window.
- `change_over_period`: ask how loss changed between the start and end of
  the window (e.g. "how did annual loss in 2023 compare with 2016?").
- Emissions trend rows (see judge_note) ask how GHG emissions from tree
  cover loss changed over the window.
- Windows stay within 2011-2023 except deliberate break-crossing rows (see
  judge_note); wording asks plainly either way.

Judge expectations: direction correct for the stated window, including
reversals; volunteered figures must match the series; figure-free but
directionally correct answers pass with unquantified=true.
