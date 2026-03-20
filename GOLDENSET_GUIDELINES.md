
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

