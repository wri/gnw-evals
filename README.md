# Global Nature Watch Agent E2E Testing

## Quickstart

Install the package and its dependencies into your env

```bash
uv sync
```

Copy env example file

```bash
cp .env.example .env
```

Then set your GNW machine user key and anthropic api key in the `.env` file,
then run the evals like this

```bash
uv run gnw_evals
```

By default this will read tests from a google sheet with
gold standard tests and evaluate the staging environment.

You can change multiple aspects of the runner like what tests to run
and parallelisation of the tests.

To see the available config options run

```bash
uv run gnw_evals --help
```

You can also set all of these variables in the `.env` file as
an alternative to passing them on the cli command.

## Overview

The E2E testing framework evaluates the complete agent workflow by testing four core tools:
1. **AOI Selection** (`pick_aoi`) - Evaluates location selection accuracy
2. **Dataset Selection** (`pick_dataset`) - Evaluates dataset choice accuracy
3. **Data Pull** (`pull_data`) - Evaluates data retrieval success
4. **Final Answer** (`generate_insights`) - Evaluates answer quality using LLM-as-a-judge

## Test Dataset Structure

### Multiple Values in Test Cases

When a test case can have multiple valid values for a field (e.g., comparing multiple AOIs, accepting multiple datasets), separate the values with semicolons (;). For example:

- `expected_aoi_ids = "IND.21_1;IND.27_1"` - Test passes if either Odisha (21) or Maharashtra (27) is selected
- `expected_dataset_id = "0;1"` - Test passes if either dataset 0 or 1 is selected
- `expected_context_layer = "driver;natural_lands"` - Test passes if either driver or natural_lands context layer is selected

### Essential Columns (Required for Tests)

The following columns are **required** for the E2E tests to run properly:

#### Core Test Data
- **`query`** - The user query to test (string)
- **`test_group`** - Test grouping for filtering (e.g., "dataset", "rel-accuracy", "abs-accuracy" etc)
- **`status`** - Test execution status:
  - `"ready"` - Test is ready to run (default for new tests)
  - `"rerun"` - Test should be re-executed (e.g., after fixing issues)
  - `"skip"` - Test should be skipped/ignored during execution

#### AOI Selection Evaluation
- **`expected_aoi_ids`** - Expected AOI identifier (e.g., "BRA", "USA.5_1", "IND.26_1"). For queries comparing multiple areas, use semicolons to separate values (e.g., "IND.21_1;IND.27_1" for Odisha and Maharashtra).
- **`expected_subregion`** - Expected subregion filter when user explicitly requests sub-administrative units. Only used when query explicitly mentions comparing or analyzing sub-units within a larger area. Valid values:
  - `"country"` - Countries within a region
  - `"state"` - States/provinces within a country
  - `"district"` - Districts within a state/province
  - `"municipality"` - Municipalities within a district
  - `"locality"` - Localities within a municipality
  - `"neighbourhood"` - Neighborhoods within a locality
  - `"kba"` - Key Biodiversity Areas
  - `"wdpa"` - Protected areas (World Database on Protected Areas)
  - `"landmark"` - Geographic landmarks

  **Examples:**
  - Query: "Compare deforestation across states in Brazil" → `expected_subregion: "state"`
  - Query: "Show districts in Odisha with highest alerts" → `expected_subregion: "district"`
  - Query: "Deforestation in Brazil" (no sub-unit mentioned) → `expected_subregion: ""` (empty)

#### Dataset Selection Evaluation
- **`expected_dataset_id`** - Expected dataset ID (0-8 for current datasets). For queries that may match multiple datasets, separate IDs with semicolons (e.g., "0;1" for DIST-ALERT and another dataset).
- **`expected_context_layer`** - Expected context layer (varies by dataset). Multiple values can be separated by semicolons if multiple layers are acceptable.

#### Data Pull Evaluation
- **`expected_start_date`** - Expected start date (YYYY-MM-DD). For date ranges, use the earliest expected date.
- **`expected_end_date`** - Expected end date (YYYY-MM-DD). For date ranges, use the latest expected date.

#### Answer Quality Evaluation
- **`expected_answer`** - Expected answer text for LLM-as-a-judge comparison

### Optional Columns (For Review/Analysis)

These columns are helpful for test management but not required for execution:

- **`expected_aoi_name`** - Human-readable AOI name (for review)
- **`expected_aoi_source`** - Expected AOI source (for review, not evaluated)
- **`expected_aoi_subtype`** - Expected AOI subtype (for review, not evaluated)
- **`expected_dataset_name`** - Human-readable dataset name (for review)
- **`priority`** - Test priority ("high", "medium", "low")

## Available Datasets

For the complete list of available datasets with their IDs, names, context layers, date ranges, and other details, refer to:

**`/src/tools/analytics_datasets.yml`**

This YAML file contains the authoritative dataset definitions including:
- `dataset_id` - Use for `expected_dataset_id` field
- `dataset_name` - Human-readable name
- `context_layers` - Available values for `expected_context_layer` field
- `start_date` / `end_date` - Valid date ranges for `expected_start_date` / `expected_end_date`
- `content_date` - Coverage period description
- `resolution`, `update_frequency`, and other metadata

**Key Points:**
- Dataset IDs currently range from 0-8
- Only Dataset ID 0 (DIST-ALERT) has context layers: `driver`, `natural_lands`, `grasslands`, `land_cover`
- Most datasets have no context layers (use empty string or null for `expected_context_layer`)
- Date ranges vary by dataset - check `start_date`/`end_date` fields in YAML

## Tool Evaluation Details

### 1. AOI Selection (`evaluate_aoi_selection`)

**Scoring System (Additive):**
- AOI ID match: 0.75 points
- Subregion match: 0.25 points
- **Total possible: 1.0**

**Key Features:**
- Handles GADM ID normalization (e.g., "USA.5_1" → "usa.5.1")
- Supports clarification detection via LLM-as-a-judge
- Empty expected_subregion treated as positive match

**Evaluated Fields:**
```python
{
    "aoi_score": 0.0-1.0,
    "actual_id": "selected_aoi_id",
    "actual_name": "selected_aoi_name",
    "actual_subtype": "selected_subtype",
    "actual_source": "selected_source",
    "actual_subregion": "selected_subregion",
    "match_aoi_id": True/False,
    "match_subregion": True/False
}
```

### 2. Dataset Selection (`evaluate_dataset_selection`)

**Scoring System (Additive):**
- Dataset ID match: 0.75 points
- Context layer match: 0.25 points
- **Total possible: 1.0**

**Key Features:**
- Supports clarification detection via LLM-as-a-judge
- Empty expected_context_layer treated as positive match
- String normalization for comparison

**Evaluated Fields:**
```python
{
    "dataset_score": 0.0-1.0,
    "actual_dataset_id": "selected_dataset_id",
    "actual_dataset_name": "selected_dataset_name",
    "actual_context_layer": "selected_context_layer"
}
```

### 3. Data Pull (`evaluate_data_pull`)

**Scoring System (Additive):**
- Data retrieval success: 0.75 points (row_count >= min_rows)
- Date range match: 0.25 points
- **Total possible: 1.0**

**Key Features:**
- Configurable minimum row threshold (default: 1)
- Date string normalization and comparison
- Empty expected dates treated as positive match
- Supports clarification detection

**Evaluated Fields:**
```python
{
    "pull_data_score": 0.0-1.0,
    "row_count": actual_row_count,
    "min_rows": minimum_expected_rows,
    "data_pull_success": True/False,
    "date_success": True/False,
    "actual_start_date": "actual_start_date",
    "actual_end_date": "actual_end_date"
}
```

### 4. Final Answer (`evaluate_final_answer`)

**Scoring System:**
- LLM-as-a-judge binary scoring: 0 or 1
- **Total possible: 1.0**

**Key Features:**
- Uses Haiku model for evaluation
- Compares expected vs actual answer semantically
- Extracts insights from charts_data or final messages
- Handles Gemini's list-based content structure

**Evaluated Fields:**
```python
{
    "answer_score": 0.0-1.0,
    "actual_answer": "generated_insight_text"
}
```

## Running E2E Tests

Simple end-to-end agent test runner with support for both local and API testing.

### Usage Examples

#### Basic usage
```bash
# Basic run with API token as argument
python -m gnw_evals.core --api-token your_token

# Or set API token via environment variable
export API_TOKEN=your_token
python -m gnw_evals.core

# With custom API endpoint
python -m gnw_evals.core --api-token your_token --api-base-url http://localhost:8000

# Run specific number of tests
python -m gnw_evals.core --api-token your_token --sample-size 5
```

#### Filter by test group
```bash
python -m gnw_evals.core --api-token your_token --test-group-filter rel-accuracy
python -m gnw_evals.core --api-token your_token --test-group-filter dataset --sample-size 10
```

#### Filter by status
```bash
# Run only tests with status "ready"
python -m gnw_evals.core --api-token your_token --status-filter ready

# Run tests with status "ready" or "rerun"
python -m gnw_evals.core --api-token your_token --status-filter ready,rerun
```

#### Custom output filename (timestamp always appended)
```bash
python -m gnw_evals.core --api-token your_token --output-filename my_test_run
python -m gnw_evals.core --api-token your_token --output-filename alerts_test --test-group-filter alerts
```

#### Parallel execution
```bash
python -m gnw_evals.core --api-token your_token --num-workers 10 --sample-size 20
python -m gnw_evals.core --api-token your_token --num-workers 5
```

#### Sampling configuration
```bash
# Use specific random seed for reproducible sampling
python -m gnw_evals.core --api-token your_token --random-seed 123 --sample-size 10

# Start sampling from a specific offset
python -m gnw_evals.core --api-token your_token --offset 5 --sample-size 10
```

#### Custom test file
```bash
python -m gnw_evals.core --api-token your_token --test-file data/my_custom_tests.csv
```

#### Get help
```bash
python -m gnw_evals.core --help
```

### Command Line Arguments

#### Required Arguments
- **`--api-token`** - Bearer token for API authentication (required, can also be set via `API_TOKEN` environment variable)

#### Optional Arguments
- **`--api-base-url`** - API endpoint URL (default: `http://localhost:8000`)
- **`--sample-size`** - Number of test cases to run (default: `1`, use `-1` for all rows)
- **`--test-file`** - Path to CSV test file (default: `data/e2e_test_dataset.csv`)
- **`--test-group-filter`** - Filter tests by test_group column (optional)
- **`--status-filter`** - Filter tests by status column, comma-separated (e.g., `ready,rerun`)
- **`--output-filename`** - Custom filename for results (timestamp will be appended)
- **`--num-workers`** - Number of parallel workers (default: `1`)
- **`--random-seed`** - Random seed for sampling (default: `0`, means no random sampling)
- **`--offset`** - Offset for getting subset (default: `0`, ignored if random_seed is 0)

## Output Files

Tests generate two CSV files in `data/tests/`:

1. **`*_summary.csv`** - Query and scores only
2. **`*_detailed.csv`** - Expected vs actual values side-by-side


## Scoring Summary

**Overall Score Calculation:**
```
overall_score = (aoi_score + dataset_score + pull_data_score + answer_score) / 4
```

**Pass Threshold:** ≥ 0.7 (70%)

**Individual Tool Weights:**
- Each tool contributes equally (25%) to overall score
- Within each tool, sub-components have different weights as documented above

## Test Data Requirements Summary

### Minimum Required Columns for Functional Tests:
```
query, expected_aoi_ids, expected_subregion, expected_dataset_id,
expected_context_layer, expected_start_date, expected_end_date,
expected_answer, test_group, status
```

### Optional for Review/Management:
```
expected_aoi_name, expected_aoi_source, expected_aoi_subtype,
expected_dataset_name, priority
```

## Gold Standard Test Set Guidelines

A gold standard test set should be a curated subset of 20-50 high-quality queries that:
- **Always run end-to-end without failure**
- **Never require agent clarification**
- **Have complete, unambiguous inputs** (AOI, dataset, date range, task)
- **Have objective, verifiable answers**

### Characteristics of Gold Standard Tests

#### 1. Complete Query Specification
Queries must be self-contained with all required information:

**✅ Good Examples:**
- `"Which 5 states in India had the most tree cover loss during 2020-2022?"`
- `"How much cropland area did Nigeria have in 2020 compared to Ghana?"`
- `"What was the total deforestation in Brazilian Amazon states from 2019-2021?"`

**❌ Avoid Ambiguous Queries:**
- `"Show me deforestation"` (missing location, timeframe)
- `"Compare forest loss"` (missing what to compare)
- `"Recent alerts in the region"` (vague location and timeframe)

#### 2. Objective, Measurable Answers
Answers should be specific facts, numbers, or rankings that can be verified:

**✅ Objective Answers:**
- `"Chhattisgarh (45.2 kha), Odisha (38.7 kha), Jharkhand (31.4 kha), Madhya Pradesh (28.9 kha), Maharashtra (24.1 kha)"`
- `"Nigeria: 34.2 million hectares, Ghana: 8.7 million hectares"`
- `"Pará: 2.1 Mha, Amazonas: 1.8 Mha, Rondônia: 0.9 Mha"`

**❌ Avoid Subjective Answers:**
- `"Some states had significant loss"`
- `"Forest conditions are concerning"`
- `"The situation has worsened"`

#### 3. Test Data Requirements

For gold standard tests, you only need these minimal fields:

```csv
query,expected_answer,test_group,status
```

**Optional fields** (if you want to validate individual tools):
```csv
expected_aoi_id,expected_subregion,expected_dataset_id,expected_context_layer,expected_start_date,expected_end_date
```

**Note:** For gold standard, set `test_group="gold"` and focus on final answer quality only. Individual tool validation is optional since the goal is end-to-end success without clarification.

### Gold Standard Query Templates

#### Ranking/Comparison Queries
```
"Which [N] [administrative_units] in [country] had the most [metric] from [start_year] to [end_year]?"

Examples:
- "Which 5 states in India had the most tree cover loss from 2020 to 2022?"
- "Which 3 provinces in Canada have the highest natural grassland area in 2020?"
- "Which districts in Odisha, India had the most disturbance alerts in 2024?"
```

#### Quantitative Comparison Queries
```
"How much [metric] did [location_A] have compared to [location_B] in [year/period]?"

Examples:
- "How much cropland did Brazil have compared to Argentina in 2020?"
- "What percentage of tree cover did Kalimantan Barat lose from 2001-2024?"
- "How many deforestation alerts occurred in protected areas of Peru vs Colombia in 2023?"
```

#### Trend Analysis Queries
```
"Did [metric] in [location] increase or decrease from [start_period] to [end_period]?"

Examples:
- "Did tree cover loss in Russia increase or decrease from 2020-2024?"
- "Has natural grassland area in Mongolia increased or decreased since 2010?"
- "Did disturbance alerts in the Amazon go up or down in 2024 compared to 2023?"
```

### Gold Standard Evaluation

For gold standard tests:
- **Primary Focus:** Final answer quality (LLM-as-a-judge)
- **Success Criteria:** Agent produces complete response without clarification requests
- **Scoring:** Binary pass/fail based on answer accuracy
- **Frequency:** Run before major releases and after significant changes

## Common Issues and Troubleshooting

1. **Empty Results:** Check that `status` column contains "ready" or "rerun"
2. **AOI Mismatches:** Verify GADM ID format (e.g., "USA.5_1" not "USA_5_1")
3. **Date Format Issues:** Use consistent date format (YYYY-MM-DD)
4. **API Authentication:** Ensure `--api-token` is provided or `API_TOKEN` environment variable is set (required)
5. **Parallel Execution:** Reduce `--num-workers` if hitting rate limits
6. **Missing Arguments:** Use `--help` to see all available options and their defaults
