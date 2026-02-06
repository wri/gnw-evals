# GNW Evals - Scoring System Tasks

## Status Legend
- [ ] Not Started
- [x] Completed
- [~] In Progress

---

## 1. Clarification Score Fix

### Issue
Currently scoring 1.0 for asking for clarification. This should be 0, unless we have a column specifically saying a clarification is target behavior.

**Priority:** High  
**Status:** [ ]  
**File:** `aoi_evaluator.py` (likely)

---

## 2. Multiple AOI_IDs Handling

### Issues
- Currently checking with "OR" behavior -- if actual is in expected_set, full score
- Seems if "expected" has more than one value, actual should have more than one
- The code in `aoi_evaluator.py` assumes `agent_state["aoi"]` is a single AOI object, not a list
- For comparative queries with multiple AOIs, the agent state probably contains multiple AOIs (maybe as a list or in a different structure), but the evaluator only extracts the first one

**Priority:** Medium  
**Status:** [ ]  
**File:** `aoi_evaluator.py`

---

## 3. Date Check Range Implementation

### Issue
- `evaluate_data_pull` needs date range checking to be finished
- `date_success` is false even when actual dates match expected dates
- Seems to be caused by format mismatch

**Priority:** Low
**Status:** [ ]  
**File:** Location where `evaluate_data_pull` is defined

---

## 4. GADM Normalization Logic

### Issue
Double-check GADM normalization logic to ensure it's working correctly.

**Priority:** TBD
**Status:** [ ]  
**File:** TBD

---

## 5. Answer Score - No Data Scenario

### Issue
If no charts data or answer, the answer score is zero. This seems different than providing an incorrect answer.

**Priority:** Medium
**Status:** [ ]  
**File:** `llm_judges.py`

---

## 6. Answer Score Improvements

### Issues
- Answer score is currently pass-fail (binary: either 0 or 1)
- Does the answer score use the charts_data insight, or the actual answer? 
- `llm_judges.py` seems to use `charts_data[0].get("insight", "")`
- Should break this up into groups, including ANSWER_DECISION - a simple test where a choice is easy to detect

**Priority:** Medium  
**Status:** [ ]  
**File:** `llm_judges.py`

---

## 7. Missing "Expected" Values Handling

### Issue
Missing "Expected" values should result in NAN score results, not positive scores. If no check is being done, no score should be given.

**Current Behavior:**
- This seems to be done correctly in some cases (e.g. `answer_score`) but not others
- If `expected_aoi` is empty, but `expected_subregion` is provided, the `aoi_score` is always None
- This is why `subregion_match` score should just be separated

**Priority:** High  
**Status:** [ ]  
**File:** Multiple evaluator files

---

## 8. Add Row Numbers to CSV Output

### Issue
There's no row number for the CSV, so with sampling it's hard to match result with CSV.

**Priority:** Low  
**Status:** [ ]  
**File:** CSV import logic

---

## 9. Overall Score Calculation Improvements

### Current Issues
```
Currently: overall_score = round(sum(scores) / len(scores), 2)
```

**Problems:**
- AOI, Dataset and Data Pull scores have 4 discrete values (0, 0.25, etc.). This results in incorrect "Averaging"
- Currently all scores get equal weight, but they are dependent. If AOI selection fails, answer will surely be wrong
- A perfect score for a test looks the same if only one check was made (for example, if dataset was correctly identified) or if all things are right
- Example: see row5 and row6: scores are very similar (0.2 apart) but one got the answer right, and the other skipped answer check

**Proposed Solutions:**
- Could average the pipeline (AOI, dataset, data pull) into a "pipeline avg score". Keep answer score separate
- OR, keep all scores 0/1. Create more scores if needed e.g. AOI ID match and Subregion match can be separate scores

**Priority:** Medium 
**Status:** [ ]  
**File:** Overall scoring calculation logic

---

## 10. Non-E2E Sheets Handling

### Issue
Handling the non-E2E sheets in the GNW_evals spreadsheet -- that is, the Q&A sets that are NOT "golden set"

**Problems:**
- If missing `expected_dataset_id`, etc., code should skip those checks
- Currently will display "missing expected columns"
- Need to update class `ExpectedData` so that instead of raising error, set `df[field] = ""`
- However, user needs to be made aware of which checks are being run from that test file CSV and which aren't
- Calculation of overall score will not be commensurable

**Priority:** Medium  
**Status:** [ ]  
**File:** `ExpectedData` class definition

---

## 11. Analysis Results - New LLM Judge

### Issue
Analysis Results will likely need a new LLM as a Judge.

**Problems:**
- Current one is written for textual answers (A/B, true/false, multiple choice), not quantitative ones (comparing 211 kha to 210.8 kha) with a tolerance, etc.
- Will need to route or separate out numeric vs textual
- Set (5) contains both types; haven't tried this yet, though

**Priority:** Low
**Status:** [ ]  
**File:** `llm_judges.py`

---

## 12. Column Name Changes in Spreadsheet

### Required Changes
Before CSV export, need these column name changes in "GNW eval sets" spreadsheet:

1. **GOLD:** okay (no change needed)
2. **Loc:** `expected_id` → `expected_aoi_ids`
3. **Dataset:** `expected_dataset` → `expected_dataset_id`
4. **Analysis:** `expected_result_standardized` → `expected_answer` + add `expected_dataset_id`

**Priority:** Medium  
**Status:** [ ]  
**File:** Spreadsheet template / data ingestion logic

---

## Next Steps

1. Reorder
2. For each task -- one be one: create git branch, diagnose and plan a solution, implement solution, update tasks.md, then merge to dev
3. Submit PR to merge to main 
