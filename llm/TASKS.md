# GNW Evals - Scoring System Tasks

## Status Legend
- [ ] Not Started
- [x] Completed
- [~] In Progress

---

# PR #1: FIXES & CORRECTIONS

**Branch:** `fix/scoring-corrections`  
**Target:** `main`  
**Execute in order (respecting dependencies)**

---

## Task 1: Missing "Expected" Values Handling ⭐ FOUNDATIONAL

**Priority:** High  
**Status:** [x]  
**Category:** Fix

### Problem
Missing "Expected" values should result in `None` (NaN) score results, not positive scores. If no check is being done, no score should be given. Previously, empty expected values were treated as positive matches, awarding points incorrectly.

### Old Behavior
- Empty `expected_subregion` → treated as match (0.25 points awarded)
- Empty `expected_context_layer` → treated as match (0.25 points awarded)
- Missing expected dates → treated as match (0.25 points awarded)
- Missing `expected_answer` → correctly returned `None`
- Additive scoring: AOI (0.75 + 0.25), Dataset (0.75 + 0.25), Data Pull (0.75 + 0.25)

### Updated Behavior
- Refactored to **separate binary scores** (0/1/None) for each check component:
  - `aoi_id_match_score` (0/1/None) - returns None if no `expected_aoi_ids`
  - `subregion_match_score` (0/1/None) - returns None if no `expected_subregion`
  - `dataset_id_match_score` (0/1/None) - returns None if no `expected_dataset_id`
  - `context_layer_match_score` (0/1/None) - returns None if no `expected_context_layer`
  - `data_pull_exists_score` (0/1) - checks if data was pulled successfully
  - `date_match_score` (0/1/None) - returns None if no expected dates
  - `answer_score` (0/1/None) - returns None if no `expected_answer`
- Overall score calculation excludes `None` values from averaging
- Never awards points for missing expected values
- CSV exports now include 7 separate score columns instead of 4 combined scores

### Implementation Details
- Modified 8 files: `eval_types.py`, 3 evaluators, `base.py`, `result_exporter.py`, `core.py`, and test file
- Added 7 new unit tests validating the new behavior
- All 11 tests pass (4 integration + 7 unit tests)

---

## Task 2: Clarification Score Fix

**Priority:** High  
**Status:** [x]  
**Category:** Fix

### Problem
Currently scoring 1.0 (full points) when agent asks for clarification. This should be 0.0, unless there's a column specifically indicating clarification is expected/target behavior.

### Old Behavior
Clarification requests returned score of 1.0 in:
- AOI evaluator (lines 53-54)
- Dataset evaluator (lines 44-45)
- Data pull evaluator (lines 37-38)

### Updated Behavior
- Added `expected_clarification: bool` field (defaults to `False`) to ExpectedData and TestResult
- Added `clarification_requested_score: float | None` field to TestResult
- Clarification scoring logic:
  - If `expected_clarification=True` AND agent requests clarification → `clarification_requested_score = 1.0`
  - If `expected_clarification=False` AND agent requests clarification → `clarification_requested_score = 0.0`
  - If no clarification requested → `clarification_requested_score = None`
- When clarification is given, other scores (aoi_id, dataset_id, etc.) are set to `None` (not applicable)
- `answer_score` is evaluated independently - if `expected_answer` is provided, it's evaluated regardless of clarification expectations
- Overall score calculation includes `clarification_requested_score` when `expected_clarification=True`
- CSV exports include `clarification_requested_score` and `expected_clarification` columns

### Implementation Details
- Modified 8 files: `eval_types.py`, 3 evaluators (`aoi_evaluator.py`, `dataset_evaluator.py`, `data_pull_evaluator.py`), `answer_evaluator.py`, `base.py`, `result_exporter.py`, and test file
- Added 3 new unit tests validating the new behavior
- All 14 tests pass (4 integration + 7 Task 1 unit tests + 3 Task 2 unit tests)

---

## Task 3: Answer Score - No Data Scenario

**Priority:** Medium  
**Status:** [ ]  
**Category:** Fix

### Problem
If no charts data or answer, the answer score is zero. This seems different than providing an incorrect answer.

### Expected Behavior
Distinguish between:
- No data/answer provided → return `None` (check not applicable)
- Incorrect answer provided → return score 0.0

---

## Task 4: Answer Score Improvements

**Priority:** Medium  
**Status:** [ ]  
**Category:** Fix

### Problems
- Answer score is currently pass-fail (binary: either 0 or 1)
- Uses `charts_data[0].get("insight", "")` - is this the right source?
- Should break this up into groups, including ANSWER_DECISION - a simple test where a choice is easy to detect

### Proposed Improvements
- Consider more granular scoring options
- Verify using correct answer source
- Add support for different answer types (decision vs quantitative)

---

## Task 5: Overall Score Calculation Improvements

**Priority:** Medium  
**Status:** [~]  
**Category:** Fix

### Current Issues (PARTIALLY RESOLVED)
```
Old: overall_score = round(sum(scores) / len(scores), 2)  # Included None values, 0.25 increments
```

**Problems:**
- ~~AOI, Dataset and Data Pull scores have 4 discrete values (0, 0.25, 0.5, 0.75, 1.0)~~ ✅ FIXED in Task 1
- Currently all scores get equal weight, but they are dependent. If AOI selection fails, answer will surely be wrong
- ~~A perfect score for a test looks the same if only one check was made vs. if all checks passed~~ ✅ FIXED in Task 1
- ~~Example: row5 and row6 scores are very similar (0.2 apart) but one got the answer right, and the other skipped answer check~~ ✅ FIXED in Task 1

### Completed in Task 1
- ✅ All scores now binary 0/1 (no more 0.25 increments)
- ✅ Separate scores for each component (7 total score fields)
- ✅ Overall score excludes None values from averaging
- ✅ Scores only calculated when expected values are present

### Remaining Work
- Weighted scoring: Consider giving different weights to different checks
- Pipeline grouping: Average pipeline (AOI, dataset, data pull) separately from answer score
- Dependency modeling: Account for dependent checks (e.g., if AOI fails, downstream likely fails)

---

## Task 6: Date Check Range Implementation

**Priority:** Low  
**Status:** [ ]  
**Category:** Fix

### Problem
- `evaluate_data_pull` needs date range checking to be finished
- `date_success` is false even when actual dates match expected dates
- Seems to be caused by format mismatch

---

## Task 7: GADM Normalization Logic

**Priority:** TBD  
**Status:** [ ]  
**Category:** Fix

### Problem
Double-check GADM normalization logic to ensure it's working correctly.

---

# PR #2: NEW FEATURES

**Branch:** `feature/new-capabilities`  
**Target:** `main`

---

## Task 8: Multiple AOI_IDs Handling

**Priority:** Medium  
**Status:** [ ]  
**Category:** New Feature

### Problem
- Currently checking with "OR" behavior -- if actual is in expected_set, full score
- Seems if "expected" has more than one value, actual should have more than one
- The code in `aoi_evaluator.py` assumes `agent_state["aoi"]` is a single AOI object, not a list
- For comparative queries with multiple AOIs, the agent state probably contains multiple AOIs (maybe as a list or in a different structure), but the evaluator only extracts the first one

### Expected Behavior
Support evaluation of queries that require multiple AOIs for comparison.

---

## Task 9: Add Row Numbers to CSV Output

**Priority:** Low  
**Status:** [ ]  
**Category:** New Feature

### Problem
There's no row number for the CSV, so with sampling it's hard to match result with CSV.

### Expected Behavior
Add row numbers to CSV output for easier tracking and debugging.

---

## Task 10: Non-E2E Sheets Handling

**Priority:** Medium  
**Status:** [ ]  
**Category:** New Feature

### Problem
Handling the non-E2E sheets in the GNW_evals spreadsheet -- that is, the Q&A sets that are NOT "golden set"

**Current Issues:**
- If missing `expected_dataset_id`, etc., code should skip those checks
- Currently will display "missing expected columns"
- Need to update class `ExpectedData` so that instead of raising error, set `df[field] = ""`
- However, user needs to be made aware of which checks are being run from that test file CSV and which aren't
- Calculation of overall score will not be commensurable

---

## Task 11: Analysis Results - New LLM Judge

**Priority:** Low  
**Status:** [ ]  
**Category:** New Feature

### Problem
Analysis Results will likely need a new LLM as a Judge.

**Current Limitations:**
- Current judge is written for textual answers (A/B, true/false, multiple choice), not quantitative ones (comparing 211 kha to 210.8 kha) with a tolerance, etc.
- Will need to route or separate out numeric vs textual
- Set (5) contains both types; haven't tried this yet, though

### Expected Behavior
Add numeric comparison judge with tolerance support for quantitative analysis results.

---

## Task 12: Column Name Changes in Spreadsheet

**Priority:** Medium  
**Status:** [ ]  
**Category:** New Feature

### Required Changes
Before CSV export, need these column name changes in "GNW eval sets" spreadsheet:

1. **GOLD:** okay (no change needed)
2. **Loc:** `expected_id` → `expected_aoi_ids`
3. **Dataset:** `expected_dataset` → `expected_dataset_id`
4. **Analysis:** `expected_result_standardized` → `expected_answer` + add `expected_dataset_id`

also
* need a clarification expected column in the golden set. Add a few example rows 


--- 

# notes 

things to look into later: 
* Currently data pull is only evaluated if expected_dataset_id exists. Should we make data pull checks independent?
* a bitmap style cheatsheet of results where each row is a eval row, and each column is a test score: neutral if None, green/red for pass/fail scores. 
* write a file that explains all the scores and how they are calculated. input column from spreadsheet --> logic --> output score. remove this from the readme

reminders: 
* make sure readme.md is updated 
* simplify the unittests. They're getting lengthly
* before PRs, get rid of the references to "Task 1 / 2" etc. Those were emphemeral 
