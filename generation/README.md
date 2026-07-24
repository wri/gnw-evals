# Case generation

Tooling for producing eval cases per intent x dataset cell. The design
principle: **the LLM only ever writes prompt wordings; every expected value
is constructed mechanically** from the permutation manifest, so generated
cases cannot smuggle in wrong expectations.

## Layout

```
cases/
  tree_cover_loss__quantification.csv    promoted cases (one file per cell)
  tree_cover_loss__comparison.csv
  tree_cover_loss__trend.csv
  manifests/
    tree_cover_loss__<intent>.manifest.csv   the permutation manifest per cell
  candidates/                            generated, not yet promoted (gitignored
                                         by workflow: promote or delete)
generation/
  tree_cover_loss/_shared.md             prompt-wording rules for the dataset
  tree_cover_loss/<intent>.md            per-intent rules and subtype notes
  validate_manifest.py                   manifest validity + coverage report
  generate_cases.py                      LLM wording generation
```

## The manifest

One row per permutation a well-tested cell should cover: subtype x
parameters x context layer x AOI x date-expression class x language x
phrasing style. It is the **prompt-coverage denominator**: coverage = rows
with at least one promoted case / rows. `n_cases` sets the wording target
per row (variants add robustness, not coverage).

Manifests are curated by hand. Each manifest's dataset is resolved from its
filename via `generation/dataset_config.py`, and it is validated against that
dataset's catalog YAML (legal canopy values, context layers, year range,
plus per-dataset applicability — e.g. trend is rejected for snapshot
datasets):

```bash
uv run python generation/validate_manifest.py \
  --catalog-dir ../project-zeno/src/agent/datasets/catalog
```

Axis values not yet represented (relative dates, unstated-date defaults,
non-English languages) are deliberately absent from the manifests until the
harness can score them; the coverage tier reflects that honestly rather
than pretending the axis is covered.

## Generating cases

```bash
uv run python generation/generate_cases.py \
  --dataset tree_cover_loss --intent quantification [--dry-run]
```

For every manifest row below its `n_cases` target the script asks the LLM
(default `claude-sonnet-5`) for the missing wordings, passing the
instruction files plus the row's existing wordings (to force variety), and
writes full case rows to `cases/candidates/`. Dates, AOI ids, dataset id,
canopy, filters, crop/gas focus and judge instructions come from the
manifest and the dataset's `dataset_config.py` entry, never from the LLM.
`--dataset` accepts any slug in `dataset_config.py`; the script refuses an
intent that config marks not applicable to the dataset.

## Spot-check and promotion (the review gate)

1. Read every candidate wording against `generation/<dataset>/_shared.md`:
   terminology picks the layer, thresholds stated iff non-default, dates
   explicit, one analytics query per prompt.
2. Review 100% of `judge_instruction` values (they steer scoring).
3. Promote by appending to the main `cases/*.csv` with `status=ready`
   (candidates carry `status=candidate`); delete the candidates file.
4. Re-run `validate_manifest.py`: it reports coverage and rows still below
   target.
5. Every case that fails its first eval run gets triaged (bad case vs real
   defect) before the case set is treated as versioned.

## Adding a new cell (dataset x intent)

1. Write the manifest (start from an existing one; keep required axes
   exhaustive, long-tail axes sampled).
2. Write `generation/<dataset_slug>/_shared.md` from the dataset's catalog
   YAML (`prompt_instructions` and `cautions` are the raw material) plus a
   per-intent file.
3. If the dataset's analytics endpoint is new, extend
   `src/gnw_evals/utils/analytics_client.py` first (ground truth must be
   fetchable) and generalise `generate_cases.py`'s dataset constants.
4. Generate, spot-check, promote, validate.
