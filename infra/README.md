# GNW Evals Infrastructure

CloudFormation stack for hosting the GNW eval results viewer on AWS Amplify, with eval CSV data served from a private S3 bucket via CloudFront.

There are two ways to deploy the Amplify frontend:

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
                                         │ Amplify            │
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
./scripts/package_amplify.sh

# Or point at a different CSV directory
./scripts/package_amplify.sh --outputs-dir /path/to/csvs
```

Then upload `amplify-deploy.zip` via the Amplify Console (see step 4A below). To update results later, re-run the script and re-upload.

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
| `CloudFrontDomainName` | `CLOUDFRONT_BASE` in `simple.py` and `index.html`, or `--cloudfront-url` for `package_amplify.sh` |
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
./scripts/package_amplify.sh --cloudfront-url https://dXXXXXXXXXX.cloudfront.net/
```

### 4. Create the Amplify app

#### Option A: Deploy without Git (recommended for quick setup)

No GitHub connection needed. Package the app as a zip and upload manually:

```bash
# Self-contained: bundles CSVs from outputs/ into the zip
./scripts/package_amplify.sh

# With CloudFront: data fetched at runtime, no CSVs bundled
./scripts/package_amplify.sh --cloudfront-url https://dXXXXXXXXXX.cloudfront.net/
```

Then in the AWS Console:

1. Go to **AWS Amplify**
2. **New app** > **Host web app** > **Deploy without Git provider**
3. Upload `amplify-deploy.zip`
4. Under **Access control**, enable password protection

To update with new eval results, re-run the script and upload the new zip.

#### Option B: Deploy via GitHub

1. Go to **AWS Amplify** in the console
2. **New app** > **Host web app** > connect your GitHub repo
3. Select the branch (e.g. `main`)
4. Amplify will detect `amplify.yml` in the repo root automatically
5. Under **Access control**, enable password protection

### 5. Update the stack with the Amplify domain

Once the Amplify app is deployed and you have its URL (e.g. `https://main.d1abc2def3.amplifyapp.com`), update the stack so CloudFront's CORS policy allows requests from it:

```bash
./infra/deploy.sh --profile <your-sso-profile> \
  --amplify-domain https://main.d1abc2def3.amplifyapp.com
```

> **Note:** This step is only needed for CloudFront-backed mode. Self-contained zips serve data from the same origin, so CORS is not involved.

### 6. Upload initial eval data

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
| `scripts/package_amplify.sh` | Package `index.html` (+ optional CSV data) into a zip for manual Amplify deployment |


## Updating the stack

To change parameters or update resources:

```bash
./infra/deploy.sh --profile <your-sso-profile> \
  --amplify-domain https://main.d1abc2def3.amplifyapp.com \
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

The Amplify app must be deleted separately from the Amplify Console.