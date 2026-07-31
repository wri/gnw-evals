# Scoring Methodology

## Overview

The evaluation system compares agent behavior against expected values from a test spreadsheet. Each test row contains a `query` field and various `expected_*` fields that define what the agent should produce.

**Core Principle:** Scores are only generated when an `expected_*` value is provided. If no expected value exists for a particular check, that check returns `None` and is excluded from scoring.

All individual scores are **binary** (0 or 1) or `None`:
- **1** = Pass (agent output matches expected)
- **0** = Fail (agent output does not match expected)
- **None** = Not evaluated (no expected value provided)

The following comparisons (i.e. between expected and actual values) are performed using LLM-as-a-Judge
* Answer quality evaluation (`charts_answer_score`, `agent_answer_score`)
* Clarification detection (`clarification_requested_score`)

All LLM-as-a-Judge checks run on **Claude Haiku 4.5** (`claude-haiku-4-5`, via LangChain's `ChatAnthropic`), as configured in `src/gnw_evals/utils/models.py`.

## Individual Score Components

### AOI (Area of Interest) Selection

**1. AOI ID Match Score** (`aoi_id_match_score`)
- **Comparison:** Hard logic with normalization
  - For GADM IDs: Normalizes format (e.g., "USA.5_1" → "usa.5.1")
  - Supports multiple valid IDs (separated by semicolons in CSV)
  - Case-insensitive comparison
- **Score:** 1 if actual AOI ID matches any expected ID, otherwise 0

**2. Subregion Match Score** (`subregion_match_score`)
- **Comparison:** Hard logic with string normalization
  - Compares administrative level (e.g., "state", "district", "country")
- **Score:** 1 if actual subregion matches expected, otherwise 0

### Dataset Selection

**3. Dataset ID Match Score** (`dataset_id_match_score`)
- **Comparison:** Hard logic with string normalization
  - Supports multiple valid dataset IDs (separated by semicolons)
  - Case-insensitive comparison
- **Score:** 1 if actual dataset ID matches any expected ID, otherwise 0

**4. Context Layer Match Score** (`context_layer_match_score`)
- **Comparison:** Hard logic with string normalization
  - Supports multiple valid layers (separated by semicolons)
  - Case-insensitive comparison
- **Score:** 1 if actual context layer matches any expected layer, otherwise 0

### Data Pull

**5. Data Pull Exists Score** (`data_pull_exists_score`)
- **Comparison:** Hard logic
  - Checks if `row_count >= 1` (configurable minimum threshold)
- **Score:** 1 if data was successfully retrieved, otherwise 0

**6. Date Extraction Score** (`date_extraction_score`)
- **Evaluated when:** Both `expected_start_date` AND `expected_end_date` are provided
- **Source:** the `start_date`/`end_date` **arguments the agent passed to its own
  tools** — `pull_data`, falling back to `pick_dataset` when `pull_data` carries no
  dates. Read from `agent_state["messages"]` tool calls, not from recorded state.
- **Comparison:** Hard logic with date normalization (M/D/YYYY, YYYY-MM-DD, YYYY)
- **Score:** 1 if any dated tool call matches both expected dates, otherwise 0.
  A row that pulls more than once passes if any call matches. `None` if no dates were
  expected, or the expected dates are unparseable. `0` if dates were expected but the
  agent never scoped a period at all.
- **Also reported:** `actual_extracted_start_date`, `actual_extracted_end_date`,
  `date_extraction_source` (which tool supplied them), `actual_extracted_windows`
  (every window observed, for diagnosis)

**6b. Date Coverage Score** (`date_coverage_score`) — *informational, not scored*
- **Evaluated when:** Both expected dates are provided
- **Source:** `agent_state["start_date"]`/`["end_date"]`, falling back to the latest
  `statistics` entry
- **Comparison:** **containment**, not equality — passes when the recorded range
  *contains* the requested range
- **Score:** 1 if the recorded range covers the request, otherwise 0
- **Excluded from `overall_score` by design.** The recorded range is inconsistent
  about what it holds: for the same query it has been observed recording the
  requested window, the dataset's full coverage extent (e.g. 2001–2025 for Hansen),
  and a rolling window ending today. The agent legitimately pulls a wider range and
  slices in code, so an exact-match check penalised correct behaviour — on one full
  gold run, 8 of 9 date failures were rows that had extracted and answered the right
  year. Containment is the only claim the recorded range can support, and it still
  fails usefully when the pull genuinely misses part of the requested period.

> **Renamed:** this check was `date_match_score` before 2026-07-30. Results CSVs
> written prior to that use the old column name.

### Answer Quality

**7. Charts Answer Score** (`charts_answer_score`)
- **Evaluated when:** `expected_answer` is provided AND agent produced `charts_data[0]["insight"]`
- **Comparison:** LLM-as-a-judge
  - Type-aware evaluation: boolean, numeric, year, or named entity
  - Numeric answers: tolerance-based comparison (configurable, currently 5%)
  - Boolean/year answers: exact match required
  - Named entity answers: semantic similarity
- **Score:** 1 if insight captures expected answer, otherwise 0

**8. Agent Answer Score** (`agent_answer_score`)
- **Evaluated when:** `expected_answer` is provided AND agent produced a final message
- **Comparison:** LLM-as-a-judge
  - Same evaluation logic as charts answer score
  - Evaluates raw agent response from `messages[-1].content`
- **Score:** 1 if agent message captures expected answer, otherwise 0

### Clarification Handling

**9. Clarification Requested Score** (`clarification_requested_score`)
- **Evaluated when:** Agent requests clarification instead of completing the task
- **Comparison:** LLM-as-a-judge
  - First, detects if agent response is a clarification request
  - Then, compares against `expected_clarification` flag
- **Score:**
  - 1 if clarification was expected (`expected_clarification=True`) and agent requested it
  - 0 if clarification was NOT expected (`expected_clarification=False`) but agent requested it
  - `None` if agent did not request clarification
- **Note:** When clarification is given, other scores (AOI, dataset, data pull) are set to `None` (not applicable)

### Nudge Handling

**10. Nudge Match Score** (`nudge_match_score`)
- **Evaluated when:** `expected_nudge_type` and/or `expected_nudge_options` is provided
- **Comparison:** Hard logic, read directly from the agent's `nudge` state field (`{type, options}`) - no LLM judge involved
  - Type check (when `expected_nudge_type` is set): case-insensitive exact match
  - Options check (when `expected_nudge_options` is set): actual options must include at least one expected option and none outside the expected set (same subset logic as `suggested_datasets_match_score`)
- **Score:** 1 if both applicable checks pass, otherwise 0
- **Note:** This is a deterministic substitute for `clarification_requested_score` whenever the expected clarification behavior is a specific nudge (`aoi_choice`, `dataset_choice`, or a direct `send_nudge` call) - prefer it over `expected_clarification` for those rows, since it checks exact agent state instead of an LLM's read of the response text.

## Overall Score Calculation

The overall score is computed as the **simple average** of all applicable (non-None) scores:

```
overall_score = sum(valid_scores) / count(valid_scores)
```

**Example 1:** Test with all checks
- AOI ID: 1, Dataset ID: 1, Context Layer: 1, Data Pull: 1, Date Extraction: 1, Charts Answer: 0, Agent Answer: 0
- Overall: (1+1+1+1+1+0+0) / 7 = **0.71**

Note that `date_coverage_score` does **not** enter this average even when it is
computed — see 6b above. Of the date checks, only `date_extraction_score` is scored.

**Example 2:** Test with only answer check
- AOI ID: None, Dataset ID: None, Data Pull: None, Charts Answer: 1, Agent Answer: 1
- Overall: (1+1) / 2 = **1.0**

**Example 3:** Clarification expected
- Clarification: 1, all other scores: None
- Overall: 1 / 1 = **1.0**

**Pass Threshold:** Tests are considered passing if `overall_score >= 0.7` (70%)

## Other Implementation Details

### Normalization Functions
- **GADM IDs:** Strips suffixes after underscore, converts hyphens to dots, lowercases
- **Dates:** Converts M/D/YYYY and YYYY formats to YYYY-MM-DD for comparison
- **Strings:** Lowercases and strips whitespace

### LLM-as-a-Judge Details
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5`, via LangChain)
- **Answer Type Detection:** Automatic classification as boolean, numeric, year, or named entity
- **Numeric Tolerance:** Configurable percentage-based tolerance (currently 5%)
- **Clarification Detection:** Pattern-based identification of uncertainty, questions, or requests for more information

### Multiple Values Support
When multiple values are acceptable (e.g., "IND.21_1;IND.27_1"), the test passes if the actual value matches **any** of the expected values. This is useful for:
- Comparative queries involving multiple AOIs
- Queries that could use multiple datasets
- Queries accepting multiple context layers
