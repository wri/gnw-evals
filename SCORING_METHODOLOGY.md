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

**6. Date Match Score** (`date_match_score`)
- **Evaluated when:** Both `expected_start_date` AND `expected_end_date` are provided
- **Comparison:** Hard logic with date normalization
  - Normalizes multiple date formats (M/D/YYYY, YYYY-MM-DD, YYYY)
  - Compares start and end dates separately
- **Score:** 1 if both start and end dates match expected, otherwise 0

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

## Overall Score Calculation

The overall score is computed as the **simple average** of all applicable (non-None) scores:

```
overall_score = sum(valid_scores) / count(valid_scores)
```

**Example 1:** Test with all checks
- AOI ID: 1, Subregion: 1, Dataset ID: 1, Context Layer: 1, Data Pull: 1, Date: 1, Charts Answer: 0, Agent Answer: 0
- Overall: (1+1+1+1+1+1+0+0) / 8 = **0.75**

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
- **Model:** Claude 3.5 Haiku (via LangChain)
- **Answer Type Detection:** Automatic classification as boolean, numeric, year, or named entity
- **Numeric Tolerance:** Configurable percentage-based tolerance (currently 5%)
- **Clarification Detection:** Pattern-based identification of uncertainty, questions, or requests for more information

### Multiple Values Support
When multiple values are acceptable (e.g., "IND.21_1;IND.27_1"), the test passes if the actual value matches **any** of the expected values. This is useful for:
- Comparative queries involving multiple AOIs
- Queries that could use multiple datasets
- Queries accepting multiple context layers
