# ADR 0001: Manual GitHub Action for Running Evals

## Status

Accepted

## Context

The repository currently supports local/manual eval execution via `uv run gnw_evals`, and writes CSV outputs to `outputs/`.
We need a repeatable CI/CD mechanism to run a small eval sample on demand and capture outputs as GitHub Actions artifacts.
We also need the operator to choose between staging and production APIs at run time.

Requirements for the first version:

- Trigger manually from GitHub Actions.
- Select target API environment: `staging` or `prod`.
- Use `num_workers=1` and `sample_size=5` initially for safe testing.
- Upload generated CSV outputs as workflow artifacts.
- Optionally upload the same CSV outputs to S3, but only when AWS credentials are available in environment/secrets.

## Decision

Add a new workflow at `.github/workflows/run-evals-manual.yml` with:

- `workflow_dispatch` trigger and inputs:
  - `target_env`: choice of `staging` or `prod`.
  - `eval_set`: optional eval set selector (default `gold`).
- Runtime selection of `API_BASE_URL` from `target_env`:
  - `staging` -> `https://api.staging.globalnaturewatch.org`
  - `prod` -> `https://api.globalnaturewatch.org`
- Runtime selection of `API_TOKEN` from `target_env`:
  - `staging` -> `API_TOKEN_STAGING` GitHub secret
  - `prod` -> `API_TOKEN_PROD` GitHub secret
- Eval execution via:
  - `uv sync`
  - `uv run gnw_evals --sample-size 5 --num-workers 1 --eval-set <input>`
- Artifact upload using `actions/upload-artifact` for `outputs/*.csv`.
- Optional S3 upload:
  - Always attempt as part of workflow, but only execute when AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) and bucket (`AWS_S3_BUCKET`) are present.
  - Upload path structure: `s3://<AWS_S3_BUCKET>/<target_env>/<YYYY-MM-DD>/<github.run_id>/`
  - If credentials/bucket are missing, log and skip upload without failing workflow.

## Consequences

Positive:

- Evals can be run safely on demand without local setup.
- Small default sample reduces API load and cost during validation phase.
- CSV evidence is preserved in workflow artifacts.
- S3 persistence is available when credentials are configured.

Tradeoffs:

- The first version does not schedule periodic runs.
- Production endpoint URL is assumed to be `https://api.globalnaturewatch.org`; if different, it must be updated.
- Missing secrets intentionally produce a skipped S3 upload rather than hard failure.
- The manual workflow requires separate environment tokens to be configured as
  repository/org secrets.

## Follow-ups

- Confirm and document the canonical production API URL.
- Add a scheduled workflow once manual runs are validated.
- Consider extending inputs for sample size and worker count after initial stabilization.
