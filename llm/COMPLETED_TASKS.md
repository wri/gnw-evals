# GNW Evals - Completed Tasks

## Status Legend
- [x] Completed

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
**Status:** [x]  
**Category:** Fix

### Problem
If no charts data or answer, the answer score is zero. This seems different than providing an incorrect answer. Additionally, there are two potential sources of answers: `charts_data[0]["insight"]` (structured answer) and `messages[-1].content` (raw LLM response), but only one was being evaluated.

### Old Behavior
- Single `answer_score` field evaluated only `charts_data[0]["insight"]`
- When no `charts_data` exists → `answer_score = 0` (treated as wrong answer)
- This penalized the agent twice: once for pipeline failure, again for "wrong" answer
- No visibility into agent's raw message responses

### Updated Behavior
- Split into **two separate scores**:
  - `charts_answer_score` (0/1/None) - evaluates `charts_data[0]["insight"]`
  - `agent_answer_score` (0/1/None) - evaluates `messages[-1].content`
- When no `charts_data` exists → `charts_answer_score = None` (not applicable)
- When no `messages` exist → `agent_answer_score = None` (not applicable)
- When `charts_data` exists but `insight = ""` → `charts_answer_score = 0` (evaluated as wrong)
- Both scores included in overall score when `expected_answer` is provided
- None values excluded from averaging (no double penalty)
- CSV exports now include 4 columns instead of 2: `charts_answer_score`, `agent_answer_score`, `actual_charts_answer`, `actual_agent_answer`

### Implementation Details
- Modified 6 files: `eval_types.py`, `answer_evaluator.py`, `base.py`, `result_exporter.py`, `core.py`, and test file
- Complete rewrite of `evaluate_final_answer()` to extract and evaluate both answer sources
- Added 3 new unit tests validating the new behavior
- Updated 2 existing tests to use new field names
- All 17 tests pass (4 integration + 7 Task 1 + 3 Task 2 + 3 Task 3 unit tests)

---

## Task 4: Answer Score Improvements

**Priority:** Medium  
**Status:** [x]  
**Category:** Fix

### Problem
- Answer score was binary (0/1) with basic LLM judge prompt
- Single generic prompt didn't distinguish between answer types (boolean, numeric, named entity, year)
- No tolerance handling for numeric comparisons (198.4 hectares vs 200 hectares)
- No strict matching for boolean/year answers

### Old Behavior
- Single LLM judge prompt: "Does the actual insight capture the key information?"
- Generic scoring for all answer types
- No specific rules for:
  - Boolean exact matching (TRUE/FALSE should be exact)
  - Numeric tolerance (how close is close enough?)
  - Year matching (should be exact)
  - Named entity comparison (semantic similarity)

### Updated Behavior
- Enhanced LLM judge prompt with type-specific scoring rules:
  - **BOOLEAN**: Exact semantic match (TRUE=true=yes=The statement is correct)
  - **NUMERIC**: Extract numbers and compare with 5% tolerance, ignore unit differences
  - **YEAR**: Exact match required (2015 must equal 2015)
  - **NAMED_ENTITY**: Semantic similarity (Brazil="Brazil had the most")
- Added `answer_eval_type` to structured output (for future logging/debugging)
- Maintains backward compatibility: still returns 0/1 score
- No CSV output changes

### Implementation Details
- Modified 1 file: `llm_judges.py`
- Updated `Score` class to include `answer_eval_type: str` field
- Replaced generic JUDGE_PROMPT with comprehensive prompt containing:
  - Clear type detection rules
  - Specific scoring examples for each type
  - 5% tolerance rule for numeric comparisons
  - Strict matching for boolean and year types
- All 17 existing tests pass



---


## Task 5: Overall Score Calculation Improvements

**Priority:** Medium  
**Status:** [x]  
**Category:** Fix

### Current Issues 
```
Old: overall_score = round(sum(scores) / len(scores), 2)  # Included None values, 0.25 increments
```

**Problems:**
- AOI, Dataset and Data Pull scores have 4 discrete values (0, 0.25, 0.5, 0.75, 1.0)
- A perfect score for a test looks the same if only one check was made vs. if all checks passed
- Example: row5 and row6 scores are very similar (0.2 apart) but one got the answer right, and the other skipped answer check

**Completed**
- ✅ All scores now binary 0/1 (no more 0.25 increments)
- ✅ Separate scores for each component (7 total score fields)
- ✅ Overall score excludes None values from averaging
- ✅ Scores only calculated when expected values are present

---

## Task 6: Date Check Range Implementation

**Priority:** Low  
**Status:** [x]  
**Category:** Fix

### Problem
Date range checking in `evaluate_data_pull` was failing due to format mismatch between expected dates (from CSV) and actual dates (from agent state).

### Old Behavior
- Expected dates from CSV: `M/D/YYYY` format (e.g., `1/1/2023`, `12/31/2023`)
- Actual dates from agent state: `YYYY-MM-DD` format (e.g., `2023-01-01`, `2023-12-31`)
- Comparison method: Simple string equality using `normalize_value()` (only strips whitespace)
- Result: All date comparisons failed even when dates were semantically equivalent
- `date_match_score = 0.0` for `1/1/2023` vs `2023-01-01` (same date, different format)

### Updated Behavior
- Added `normalize_date()` function to handle multiple date formats:
  - `M/D/YYYY` or `MM/DD/YYYY` (CSV format) → normalized to `YYYY-MM-DD`
  - `YYYY-MM-DD` (ISO format) → passes through unchanged
  - `YYYY` (year only) → converts to `YYYY-01-01`
  - Invalid dates or None → returns empty string (treated as missing/not evaluated)
- Updated `evaluate_data_pull()` to use `normalize_date()` instead of `normalize_value()` for date comparisons
- Dates now compared after normalization to common format
- If expected dates fail to parse (invalid), returns `date_match_score = None` (not evaluated)
- Maintains consistency with Task 1's principle: invalid/missing expected values → None score, not 0

### Implementation Details
- Modified 2 files: `utils.py` (added `normalize_date()`), `data_pull_evaluator.py` (updated date comparison logic)
- Added 3 new unit tests validating date normalization behavior
- All 20 tests pass (17 existing + 3 Task 6 unit tests)
- Validation on tests 7-11 from gold dataset shows correct behavior:
  - Slash format dates now match ISO format dates (`date_match_score = 1.0`)
  - Missing expected dates return `date_match_score = None` (not evaluated)
  - Overall date match score: 1.00 (when dates are present and comparable)

---

## Task 7: Centralized Clarification Detection

**Priority:** High  
**Status:** [x]  
**Category:** Fix / Performance

### Problem
Clarification detection duplicated across 3 evaluators, causing up to 3 LLM calls per evaluation.

### Old Behavior
- `llm_judge_clarification()` called separately in AOI, dataset, and data pull evaluators
- 1-3 LLM calls per evaluation depending on what was missing
- No `actual_clarification_requested` field in output

### Updated Behavior
- New centralized `evaluate_clarification()` called once at start of evaluation pipeline
- All evaluators run independently regardless of clarification
- Field validator distinguishes empty string (`""` → `None`) from `False`
- Added `actual_clarification_requested` field to CSV output
- 6-case truth table implemented (True/True=1.0, True/False=0.0, False/True=0.0, False/False=1.0, None/True=0.0, None/False=None)

### Performance Improvement
- Reduced from up to 3 LLM calls to exactly 1 call per evaluation (~67% reduction)

### Implementation Details
- Created: `clarification_evaluator.py`
- Modified: 8 files (models, evaluators, base runner, CSV exporter)
- Tests: Added 3 new, removed 4 old, all 23 tests pass

---

## Task 8: Column Name Changes in Spreadsheet

**Priority:** Medium  
**Status:** [x]  
**Category:** New Feature

### Changes Required
Before CSV export, these column name changes were needed in "GNW eval sets" spreadsheet:

1. **GOLD:** okay (no change needed)
2. **Loc:** `expected_id` → `expected_aoi_ids`
3. **Dataset:** `expected_dataset` → `expected_dataset_id`
4. **Analysis:** `expected_result_standardized` → `expected_answer` + add `expected_dataset_id`

Also added clarification expected column in the golden set with example rows.

---

## Task 9: Bitmap Style Cheatsheet

**Priority:** Medium
**Status:** [x]  
**Category:** New Feature

### Implementation
Created a bitmap style cheatsheet of results where each row is an eval row, and each column is a test score: neutral if None, green/red for pass/fail scores.
* prototype implemented in notebook/simple.py, 
* branch: `notebook`

---
