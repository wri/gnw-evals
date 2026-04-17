#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Upload eval CSVs to S3 via pre-signed URLs
#
# Usage:
#   ./scripts/upload_evals.sh                  # uploads all CSVs in outputs/
#   ./scripts/upload_evals.sh <prefix>         # uploads a specific run
#
# Required env vars:
#   GNW_UPLOAD_API_URL   - API Gateway endpoint (from CloudFormation output)
#   GNW_UPLOAD_API_KEY   - Shared API key (from Secrets Manager)
# ---------------------------------------------------------------------------

API_URL="${GNW_UPLOAD_API_URL:?Set GNW_UPLOAD_API_URL to the API Gateway endpoint}"
API_KEY="${GNW_UPLOAD_API_KEY:?Set GNW_UPLOAD_API_KEY to the shared API key}"
OUTPUTS_DIR="outputs"

# Determine which files to upload
if [[ $# -ge 1 ]]; then
  PREFIX="$1"
  FILES=("$OUTPUTS_DIR/${PREFIX}_summary.csv" "$OUTPUTS_DIR/${PREFIX}_detailed.csv")
else
  FILES=("$OUTPUTS_DIR"/*_summary.csv "$OUTPUTS_DIR"/*_detailed.csv)
fi

# Validate files exist
FOUND=0
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] && FOUND=$((FOUND + 1))
done

if [[ $FOUND -eq 0 ]]; then
  echo "No CSV files found to upload."
  [[ $# -ge 1 ]] && echo "Looked for: ${FILES[*]}"
  exit 1
fi

echo "Uploading $FOUND file(s)..."

# Upload each CSV
for csv in "${FILES[@]}"; do
  [[ ! -f "$csv" ]] && continue
  filename=$(basename "$csv")

  # 1. Get pre-signed URL
  presign_response=$(curl -s -X POST "$API_URL/presign" \
    -H "x-api-key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"filename\": \"$filename\"}")

  presign_url=$(echo "$presign_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")

  if [[ -z "$presign_url" || "$presign_url" == "null" ]]; then
    echo "ERROR: Failed to get pre-signed URL for $filename"
    echo "Response: $presign_response"
    exit 1
  fi

  # 2. Upload directly to S3
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$presign_url" \
    -H "Content-Type: text/csv" \
    --upload-file "$csv")

  if [[ "$http_code" == "200" ]]; then
    echo "  Uploaded $filename"
  else
    echo "  ERROR: Upload failed for $filename (HTTP $http_code)"
    exit 1
  fi
done

# 3. Finalize: regenerate manifest.json
echo "Updating manifest..."
finalize_response=$(curl -s -X POST "$API_URL/finalize" \
  -H "x-api-key: $API_KEY")

echo "Manifest updated: $finalize_response"
echo "Done."
