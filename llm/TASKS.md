# GNW Evals - Scoring System Tasks

## Status Legend
- [ ] Not Started
- [~] In Progress

**Note:** Completed tasks have been moved to `COMPLETED_TASKS.md`

---

### Task: Compare numbers in code for the chart judge

**Priority:** High
**Status:** [ ]
**Category:** Fix

`llm_judge_chart` has no numeric tolerance, and it cannot be given one in prose: it does
not compute the comparison, it asserts agreement with whatever expected value it is
handed.

Reproduced against gold 1-076's stored chart JSON, whose 25 yearly values sum to
**25.31 Mha**:

| Expected value given to the judge | True difference | Judge's claim |
|---|---|---|
| 27.4 Mha | 7.6% | "can be summed to derive the total ... 27.4 Mha ... within tolerance (0.15% difference)" |
| 26.0 Mha | 2.7% | "actual sum: 25.99 Mha, difference: 0.04%" |

Separately, on gold 1-088, it computed a difference of 1.8% correctly and then wrote
"exceeding the 2% tolerance threshold" — the arithmetic is right, the comparison is not.

Consequence today: chart rows can fail on a numeric difference well inside the tolerance
the answer judge honours (four rows in the 2026-07-31 gold run: 1-002 at 1.54%, 1-006 at
1.87%, 1-009 at 1.75%, 1-027 at 0.00%). Because `charts_answer` straddles Analysis and
Output, each one damages two failure buckets.

Also note the judge is *deterministic* per prompt — 5/5 identical verdicts on repeated
calls — so any wording change is fully attributable, and any wording change to this prompt
perturbs unrelated verdicts. Two rows (1-060, 1-076) flipped 1→0 on identical charts from
an added paragraph that never mentioned them.

Approach: have the model **extract** (`expected_value`, `actual_value`,
`values_same_quantity`) and compare in Python against `NUMERIC_TOLERANCE`, as drafted in
closed PR #40 for the answer judge. For charts the extracted `actual_value` must come from
the chart's own encoded data, which is available to the evaluator — so it can be summed in
Python rather than trusted from the model.

### Task: Create a new Overall Score

**Priority:** Low
**Status:** [ ]
**Category:** Refactor

Currently all scores get equal weight, but they are dependent. If AOI selection fails, answer will surely be wrong

Possible approaches
- Weighted scoring: Consider giving different weights to different checks
- Pipeline grouping: Average pipeline (AOI, dataset, data pull) separately from answer score
- Dependency modeling: Account for dependent checks (e.g., if AOI fails, downstream likely fails)

## Task: check GADM Normalization Logic

**Priority:** TBD
**Status:** [ ]
**Category:** Fix

Double-check GADM normalization logic to ensure it's working correctly.
- normalize_gadm_id() strips everything after _ and converts - to .   Is this okay, or might it create false positives?
- example
    - "USA.5_1" → "usa.5"
    - "USA.5_2" → "usa.5"  ← Different subregion, same normalized ID!

## Check: Multiple AOI_IDs Handling

**Priority:** Medium
**Status:** [ ]
**Category:** New Feature

Make sure the system is scoring correctly when multiple AOIs are provided either in the actual or expected fields.
* Add unittests first, ensure they are passing.
* Do the same for other fields that may contain multiple values.

Notes
- Currently checking with "OR" behavior -- if actual is in expected_set, full score
- Seems if "expected" has more than one value, actual should have more than one
- The code in `aoi_evaluator.py` assumes `agent_state["aoi"]` is a single AOI object, not a list
- For comparative queries with multiple AOIs, the agent state probably contains multiple AOIs (maybe as a list or in a different structure), but the evaluator only extracts the first one

---

## Idea: Add Row Numbers to CSV Output

**Priority:** Low
**Status:** [ ]
**Category:** New Feature

There's no row number for the CSV, so with sampling, it's hard to match result with CSV.


---

## Task: Non-E2E Sheets Handling

**Priority:** Medium
**Status:** [ ]
**Category:** New Feature


Handling the non-E2E sheets in the GNW_evals spreadsheet -- that is, the Q&A sets that are NOT "golden set"

Notes
- If missing `expected_dataset_id`, etc., code should skip those checks
- Currently will display "missing expected columns"
- Need to update class `ExpectedData` so that instead of raising error, set `df[field] = ""`
- However, user needs to be made aware of which checks are being run from that test file CSV and which aren't
- Calculation of overall score will not be commensurable

---


## Task: simplify the unittests

**Priority:** Medium
**Status:** [ ]
**Category:** Refactor

* Simplify the unittests.
* They're getting unncessarily long, the coding agents like adding a ton of tests.
* All unittests are currently in the same file.


# Additional things to look into.

Things to look into later:
* Currently data pull is only evaluated if expected_dataset_id exists. Should we make data pull checks independent?
* write a file that explains all the scores and how they are calculated. input column from spreadsheet --> logic --> output score. remove this from the readme
