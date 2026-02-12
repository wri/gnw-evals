# Global Nature Watch Agent E2E Testing

## Quickstart

Install the package and its dependencies into your env

```bash
uv sync
```

Copy the example env file and set your **GNW machine user key** and
**Anthropic API key** in the new `.env` file:

```bash
cp .env.example .env
```

Then run the evals like this

```bash
uv run gnw_evals
```

By default this will read tests from a google sheet with
gold standard tests and evaluate the staging environment.

You can change multiple aspects of the runner like what tests to run
and parallelization of the tests.

To see the available config options run

```bash
uv run gnw_evals --help
```

You can also set all of these variables in the `.env` file as
an alternative to passing them on the cli command.

## Evaluation Method Overview

The E2E testing framework evaluates the complete agent workflow by testing four core tools:

1. **AOI Selection** (`pick_aoi`) - Evaluates location selection accuracy
2. **Dataset Selection** (`pick_dataset`) - Evaluates dataset choice accuracy
3. **Data Pull** (`pull_data`) - Evaluates data retrieval success
4. **Final Answer** (`generate_insights`) - Evaluates answer quality using LLM-as-a-judge

**For detailed scoring methodology and calculation details, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

## Test Dataset Structure

### Multiple Values in Test Cases

When a test case can have multiple valid values for a field (e.g., comparing multiple AOIs, accepting multiple datasets), separate the values with semicolons (;). For example:

- `expected_aoi_ids = "IND.21_1;IND.27_1"` - Test passes if either Odisha (21) or Maharashtra (27) is selected
- `expected_dataset_id = "0;1"` - Test passes if either dataset 0 or 1 is selected
- `expected_context_layer = "driver;natural_lands"` - Test passes if either driver or natural_lands context layer is selected

### Essential Columns (Required for Tests)

The following columns are **required** in the CSV file for the E2E tests to run properly. All fields from `ExpectedData` must be present (they can be empty strings if not applicable):

#### Core Test Data

- **`query`** - The user query to test (string)
- **`test_group`** - Test grouping for filtering (e.g., "dataset", "rel-accuracy", "abs-accuracy" etc). Default: "unknown"
- **`status`** - Test execution status. Default: "ready". Use `--status-filter` to filter by status:
  - `"ready"` - Test is ready to run (default for new tests)
  - `"rerun"` - Test should be re-executed (e.g., after fixing issues)
  - `"skip"` - Test should be skipped/ignored during execution
  - **Note:** If `--status-filter` is not provided, all rows are included regardless of status

#### AOI Selection Evaluation

- **`expected_aoi_ids`** - Expected AOI identifier(s) (e.g., "BRA", "USA.5_1", "IND.26_1"). For queries comparing multiple areas, use semicolons to separate values (e.g., "IND.21_1;IND.27_1" for Odisha and Maharashtra). Can be empty if not applicable.
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
- **`expected_aoi_source`** - Expected AOI source (for reference, not evaluated)

#### Dataset Selection Evaluation

- **`expected_dataset_id`** - Expected dataset ID (0-8 for current datasets). For queries that may match multiple datasets, separate IDs with semicolons (e.g., "0;1" for DIST-ALERT and another dataset). Can be empty if not applicable.
- **`expected_context_layer`** - Expected context layer (varies by dataset). Multiple values can be separated by semicolons if multiple layers are acceptable. Can be empty if not applicable.
- **`expected_dataset_name`** - Expected dataset name (for reference, not evaluated)

#### Data Pull Evaluation

- **`expected_start_date`** - Expected start date (YYYY-MM-DD). For date ranges, use the earliest expected date. Can be empty if not applicable.
- **`expected_end_date`** - Expected end date (YYYY-MM-DD). For date ranges, use the latest expected date. Can be empty if not applicable.

#### Answer Quality Evaluation

- **`expected_answer`** - Expected answer text for LLM-as-a-judge comparison. Can be empty if not applicable.

#### Clarification Handling

- **`expected_clarification`** - Boolean flag indicating whether agent should request clarification instead of completing the task (default: `False`)

### Optional Columns (For Review/Analysis)

These columns are helpful for test management but not required for execution. The CSV loader accepts any additional columns via `extra="allow"` in the data model:

- **`priority`** - Test priority ("high", "medium", "low")
- Any other custom columns for tracking or analysis

## Running E2E Tests

Simple end-to-end agent test runner for API testing. 

Evals source. By default, gnw_evals will run tests against the live spreadsheet, 
URL specified in `utils/sheet_registry.py` 

### Usage Examples: Basic

```bash
# Basic run with manual API token specification
uv run gnw_evals --api-token your_token

# With custom API endpoint instead of GNW Staging or GNW production
uv run gnw_evals --api-token your_token --api-base-url http://localhost:8000

# Run specific number of GOLDEN SET tests (default sample size is 5)
uv run gnw_evals --api-token your_token --sample-size 10

```

Suggested basis usage
* Add the following in the .env file: 
    * API_TOKEN 
    * ANTHROPIC_API_KEY
    * SPREADSHEET_ID
    * NUM_WORKERS=5
# run first 5 rows of the LOCATION ID tests
uv run gnw_evals --sample-size 5 --eval-set location_id --output-filename "sample_locationid_evals" 

# run all tests 
uv run gnw_evals --sample-size -1 --eval-set all --output-filename "all_evals" 

```

### Usage Examples: selecting eval sets and filters

Running GOLDEN SET filters in the spreadsheet
* REMINDER: Make sure the spreadsheet is properly specified in the `.env` file using `SPREADSHEET_ID`


```bash

# Run all GOLDEN SET tests
uv run gnw_evals --api-token your_token --sample-size -1

# Filter by test group
uv run gnw_evals --api-token your_token --test-group-filter rel-accuracy

# Filter by status (comma-separated)
uv run gnw_evals --api-token your_token --status-filter ready,rerun

```

The framework supports multiple specialized eval sets, not just the GOLDEN SET
- `gold` - Full E2E golden set (default)
- `location_id` - Location/AOI identification tests
- `dataset_id` - Dataset selection tests
- `date_selection` - Date selection tests
- and others.. 

**Note:** 
- REMINDER: Make sure the spreadsheet is properly specified in the `.env` file using `SPREADSHEET_ID`
- When using `--eval-set all`, separate output files are generated for each eval set (e.g., `gold_test_TIMESTAMP.csv`, `location_id_test_TIMESTAMP.csv`, etc.)
- You cannot use `--eval-set` and `--test-file` together. Use one or the other.

```bash
# Default (gold set)
uv run gnw_evals

# Run specific eval set
uv run gnw_evals --eval-set location_id --sample-size 10

# Run all eval sets (set and forget for multi-hour runs)
uv run gnw_evals --eval-set all --sample-size -1

# Via environment variable
export EVAL_SET=dataset_id
uv run gnw_evals
```

Custom evals: Run eval tests in a local CSV  file

```bash
# Run eval tests in a custom CSV  file
uv run gnw_evals --api-token your_token --test-file data/my_tests.csv
```

## Output Files

Tests generate two CSV files in the `outputs/` directory at the project root:

1. **`outputs/*_summary.csv`** - Query and scores only
2. **`outputs/*_detailed.csv`** - Expected vs actual values side-by-side


## Scoring Summary

Individual scores are **binary** (0 or 1, or `None` if not evaluated). The overall score is the **simple average** of all applicable scores:

```
overall_score = sum(valid_scores) / count(valid_scores)
```

Scores are only calculated when the corresponding `expected_*` value is provided in the test case.

**Pass Threshold:** ≥ 0.7 (70%)

**For complete details on score calculation, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

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
expected_aoi_ids,expected_subregion,expected_dataset_id,expected_context_layer,expected_start_date,expected_end_date
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

1. **Empty Results:** Check that `status` column contains "ready" or "rerun", and use `--status-filter ready,rerun` to filter by status. Without `--status-filter`, all rows are included regardless of status.
2. **AOI Mismatches:** Verify GADM ID format (e.g., "USA.5_1" not "USA_5_1")
3. **Date Format Issues:** Use consistent date format (YYYY-MM-DD)
4. **API Authentication:** Ensure `--api-token` is provided or `API_TOKEN` environment variable is set (required)
5. **Parallel Execution:** Reduce `--num-workers` if hitting rate limits
6. **Missing Arguments:** Use `--help` to see all available options and their defaults
