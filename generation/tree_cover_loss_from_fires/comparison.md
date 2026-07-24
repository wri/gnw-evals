# Tree cover loss due to fires x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two things is larger, or how they differ. The
verifiable core is the comparative claim's direction; volunteered figures
must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` names both countries (e.g. `BRA;IDN`).
  Ask which had more fire-driven tree cover loss over the row's window. Both
  countries must appear in the prompt; the window applies to both.
- `two_period`: one country, one window that splits into the two compared
  periods. The prompt must name both sub-periods explicitly ("2011 to 2015
  compared with 2016 to 2020") and they must exactly tile the row's
  start_year-end_year window. Check the judge_note for the intended split.
- Near-zero rows (GBR, CRI): wording is normal; the small magnitudes are the
  test.
- Break-crossing rows deliberately compare across the 2011 methodology break;
  ask the comparison plainly (the caveat handling is the judge's business, not
  the wording's).

Judge expectations: direction must be correct; cited figures within a
reasonable tolerance; never report carbon emissions; figure-free but
directionally correct answers pass with unquantified=true.
