#!/bin/bash
set -euo pipefail

STACK_NAME="gnw-evals-heatmap"
TEMPLATE="$(dirname "$0")/template.yaml"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  echo "Usage: $0 --profile <aws-sso-profile> [--bucket-name <name>]"
  echo ""
  echo "Deploys the GNW evals CloudFormation stack using AWS SSO credentials."
  echo ""
  echo "Options:"
  echo "  --profile         AWS SSO profile name (required)"
  echo "  --bucket-name     S3 bucket name (default: gnw-evals-data)"
  exit 1
}

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
PROFILE=""
BUCKET_NAME="gnw-evals-data"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --bucket-name) BUCKET_NAME="$2"; shift 2 ;;
    *) usage ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  echo "Error: --profile is required"
  usage
fi

# ---------------------------------------------------------------------------
# Ensure SSO session is active
# ---------------------------------------------------------------------------
echo "Checking SSO session..."
if ! aws sts get-caller-identity --profile "$PROFILE" > /dev/null 2>&1; then
  echo "SSO session expired or not found. Logging in..."
  aws sso login --profile "$PROFILE"
fi

# ---------------------------------------------------------------------------
# Deploy stack
# ---------------------------------------------------------------------------
echo "Deploying stack '$STACK_NAME'..."
aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags "wri:project=${STACK_NAME}" \
  --parameter-overrides \
    BucketName="$BUCKET_NAME" \
  --profile "$PROFILE"

# ---------------------------------------------------------------------------
# Print outputs
# ---------------------------------------------------------------------------
echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[].[OutputKey, OutputValue]" \
  --output table \
  --profile "$PROFILE"

# Retrieve the API key value
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiKeySecretArn'].OutputValue" \
  --output text \
  --profile "$PROFILE")

echo ""
echo "API Key (for GNW_UPLOAD_API_KEY):"
aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" \
  --query "SecretString" \
  --output text \
  --profile "$PROFILE"
echo ""
