# Tree cover loss x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things is larger, or how they differ. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;IDN`).
  Ask which lost more (or to compare) over the row's window. Both countries
  must appear in the prompt; the window applies to both.
- `two_period`: one country, one window that splits into the two compared
  periods. The prompt must name both sub-periods explicitly ("2011 to 2015
  compared with 2016 to 2020") and they must exactly tile the row's
  start_year-end_year window. Check the row's judge_note for the intended
  split.
- Emissions comparison rows (see judge_note) ask which country emitted more
  GHG from tree cover loss.
- Near-zero rows (GBR, CRI): wording is normal; the small magnitudes are the
  test.
- The break-crossing row (2001-2020) deliberately compares across the 2011
  methodology break; wording should ask the comparison plainly (the caveat
  handling is the judge's business, not the wording's).

Judge expectations: direction must be correct; cited figures within 5%;
figure-free but directionally correct answers pass with unquantified=true.
