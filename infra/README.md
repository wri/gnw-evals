# GNW Evals Infrastructure

CloudFormation stack for hosting the GNW eval results viewer, with eval CSV data served from a private S3 bucket via CloudFront.

There are two ways to deploy the frontend:

- **Self-contained zip** (Option A): Bundle CSVs directly into the zip. No CloudFront/S3 infrastructure needed — skip straight to step 4A.
- **CloudFront-backed** (Option B): Deploy the full stack and upload CSVs to S3. The frontend fetches data from CloudFront at runtime.

## Architecture (CloudFront-backed mode)

```
Someone (local)                          AWS
┌──────────────┐                         ┌────────────────────┐
│ Run evals    │   POST /presign         │ API Gateway        │
│ outputs/*.csv│ ─────────────────────>  │ (API key auth)     │
└──────────────┘   (shared API key)      └────────┬───────────┘
       │                                          │
       │  gets pre-signed URL,                    v
       │  then PUTs CSV directly ──────> ┌────────────────────┐
       └────────────────────────────────>│ S3 (private)       │
                                         │  *.csv             │
                                         │  manifest.json     │
                                         └────────┬───────────┘
                                                  │ OAC
                                         ┌────────v───────────┐
                                         │ CloudFront         │
                                         │ (60s TTL, CORS)    │
                                         └────────┬───────────┘
                                                  │ fetch
                                         ┌────────v───────────┐
                                        │ GitHub Pages       │
                                         │ password-protected  │
                                         └────────────────────┘
```

### Resources created by the stack


| Resource                | Purpose                                                          |
| ----------------------- | ---------------------------------------------------------------- |
| S3 bucket               | Private storage for eval CSVs and `manifest.json`                |
| CloudFront distribution | Serves S3 data with OAC, CORS, and 60s cache TTL                 |
| CloudFront cache policy | Custom policy: 60s default TTL, 5m max TTL                       |
| Lambda (upload)         | Generates pre-signed S3 PUT URLs and regenerates `manifest.json` |
| Lambda (authorizer)     | Validates the shared API key on upload requests                  |
| API Gateway (HTTP)      | Exposes `/presign` and `/finalize` endpoints                     |
| Secrets Manager secret  | Stores the auto-generated shared API key                         |


## Prerequisites

- AWS CLI v2 installed
- An AWS SSO profile configured (`~/.aws/config`)
- Permissions: CloudFormation, S3, CloudFront, Lambda, API Gateway, IAM, Secrets Manager

## Quick start: self-contained zip (no AWS infra)

If you just want to share eval results without setting up S3/CloudFront:

```bash
# Bundles index.html + CSVs from outputs/ into a deployable zip
./scripts/package_gh_pages.sh

# Or point at a different CSV directory
./scripts/package_gh_pages.sh --outputs-dir /path/to/csvs
```

Then publish `gh-pages-deploy.zip` with GitHub Pages (see step 4A below). To update results later, re-run the script and republish.

## Full setup (CloudFront-backed)

### 1. Deploy the CloudFormation stack

```bash
./infra/deploy.sh --profile <your-sso-profile>
```

This will:

- Check your SSO session (and prompt login if expired)
- Deploy the stack with default parameters
- Print the stack outputs and the generated API key

### 2. Note the stack outputs

The deploy script prints a table with these values:


| Output                 | Used for                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| `CloudFrontDomainName` | `CLOUDFRONT_BASE` in `simple.py` and `index.html`, or `--cloudfront-url` for `package_gh_pages.sh` |
| `ApiUrl`               | `GNW_UPLOAD_API_URL` env var for `scripts/upload_evals.sh`                                        |
| `ApiKeySecretArn`      | Reference only; the API key value is printed separately                                           |


### 3. Update the CloudFront URL in source files

Replace the `XXXXXXXXXX` placeholder in both files:

`**index.html**` (line ~637):

```js
const CLOUDFRONT_BASE = "https://dXXXXXXXXXX.cloudfront.net/";
```

`**simple.py**` (line ~17):

```python
CLOUDFRONT_BASE = "https://dXXXXXXXXXX.cloudfront.net/"
```

Or, if using the zip deploy, pass it as a flag instead (no source edits needed):

```bash
./scripts/package_gh_pages.sh --cloudfront-url https://dXXXXXXXXXX.cloudfront.net/
```

### 4. Publish the frontend

#### Option A: Manual publish

No GitHub connection needed. Package the app as a zip and upload manually:

```bash
# Self-contained: bundles CSVs from outputs/ into the zip
./scripts/package_gh_pages.sh

# With CloudFront: data fetched at runtime, no CSVs bundled
./scripts/package_gh_pages.sh --cloudfront-url https://dXXXXXXXXXX.cloudfront.net/
```

Then publish with GitHub Pages from `gh-pages-deploy.zip` contents.

To update with new eval results, re-run the script and upload the new zip.

#### Option B: CI publish via GitHub Actions

Use `.github/workflows/run-evals-manual.yml`, which now packages and deploys to GitHub Pages after evals complete.

### 5. Upload initial eval data

```bash
export GNW_UPLOAD_API_URL="<ApiUrl from stack output>"
export GNW_UPLOAD_API_KEY="<API key value printed by deploy script>"

./scripts/upload_evals.sh
```

This uploads all CSVs from `outputs/` and generates `manifest.json`.

New data appears in the viewer within ~60 seconds (the CloudFront cache TTL).

## Ongoing usage

### Uploading new eval results

After running evals locally:

```bash
# Upload all CSVs in outputs/
./scripts/upload_evals.sh

# Or upload a specific run
./scripts/upload_evals.sh staging_20260213_152400

# Or point at a different directory
./scripts/upload_evals.sh --outputs-dir /path/to/csvs
./scripts/upload_evals.sh --outputs-dir /path/to/csvs staging_20260213_152400
```

The upload script:

1. Gets a pre-signed S3 URL for each CSV via the API
2. Uploads directly to S3
3. Calls `/finalize` to regenerate `manifest.json`

New data appears within ~60 seconds (CloudFront cache TTL). No redeployment needed.

### Environment variables for the upload script

Add these to your shell profile or `.env`:

```bash
export GNW_UPLOAD_API_URL="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
export GNW_UPLOAD_API_KEY="<the 40-char key from Secrets Manager>"
```

### Retrieving the API key later

```bash
aws secretsmanager get-secret-value \
  --secret-id gnw-evals-heatmap-api-key \
  --query SecretString --output text \
  --profile <your-sso-profile>
```

## Scripts reference


| Script                       | Purpose                                                                             |
| ---------------------------- | ----------------------------------------------------------------------------------- |
| `infra/deploy.sh`            | Deploy/update the CloudFormation stack                                              |
| `scripts/upload_evals.sh`    | Upload CSVs to S3 via pre-signed URLs                                               |
| `scripts/package_gh_pages.sh` | Package `index.html` (+ optional CSV data) into a zip for GitHub Pages deployment |


## Updating the stack

To change parameters or update resources:

```bash
./infra/deploy.sh --profile <your-sso-profile> \
  --bucket-name gnw-evals-data
```

## Tearing down

```bash
# Empty the S3 bucket first (CloudFormation can't delete non-empty buckets)
aws s3 rm s3://gnw-evals-data --recursive --profile <your-sso-profile>

# Delete the stack
aws cloudformation delete-stack \
  --stack-name gnw-evals-heatmap \
  --profile <your-sso-profile>
```

Any GitHub Pages site teardown is managed in repository settings.