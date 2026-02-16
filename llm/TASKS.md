# GNW Evals - Scoring System Tasks

## Status Legend
- [ ] Not Started
- [~] In Progress

---

**Note:** Completed tasks have been moved to `COMPLETED_TASKS.md`

---

# PR #2: NEW FEATURES

**Branch:** `feature/new-capabilities`  
**Target:** `main`

---

### Task 
- Currently all scores get equal weight, but they are dependent. If AOI selection fails, answer will surely be wrong

possible approaches
- Weighted scoring: Consider giving different weights to different checks
- Pipeline grouping: Average pipeline (AOI, dataset, data pull) separately from answer score
- Dependency modeling: Account for dependent checks (e.g., if AOI fails, downstream likely fails)

## Task: check GADM Normalization Logic

**Priority:** TBD  
**Status:** [ ]  
**Category:** Fix

### Problem
Double-check GADM normalization logic to ensure it's working correctly.
- normalize_gadm_id() strips everything after _ and converts - to .   Is this okay, or might it create false positives? 
- example
    - "USA.5_1" → "usa.5"
    - "USA.5_2" → "usa.5"  ← Different subregion, same normalized ID!

## Task: Multiple AOI_IDs Handling

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

## Task: Add Row Numbers to CSV Output

**Priority:** Low  
**Status:** [ ]  
**Category:** New Feature

### Problem
There's no row number for the CSV, so with sampling it's hard to match result with CSV.

### Expected Behavior
Add row numbers to CSV output for easier tracking and debugging.

---

## Task: Non-E2E Sheets Handling

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

## Task: Column Name Changes in Spreadsheet

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

# Additional things to look into. 

Things to look into later: 
* Currently data pull is only evaluated if expected_dataset_id exists. Should we make data pull checks independent?
* a bitmap style cheatsheet of results where each row is a eval row, and each column is a test score: neutral if None, green/red for pass/fail scores. 
* write a file that explains all the scores and how they are calculated. input column from spreadsheet --> logic --> output score. remove this from the readme

reminders: 
* make sure readme.md is updated 
* simplify the unittests. They're getting lengthy
