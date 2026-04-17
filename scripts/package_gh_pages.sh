#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Package index.html (+ optional local CSV data) into a zip for manual
# GitHub Pages deployment.
#
# Usage:
#   # Self-contained: bundle CSVs from outputs/ so the app works standalone
#   ./scripts/package_gh_pages.sh
#
#   # With CloudFront: index.html fetches data from CloudFront at runtime
#   ./scripts/package_gh_pages.sh --cloudfront-url https://dXXXXXXXXXX.cloudfront.net/
#
#   # Custom CSV source directory
#   ./scripts/package_gh_pages.sh --outputs-dir /path/to/csvs
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX_SRC="$REPO_ROOT/index.html"
OUT_DIR="$REPO_ROOT/dist"
OUT_ZIP="$REPO_ROOT/gh-pages-deploy.zip"

CLOUDFRONT_URL=""
OUTPUTS_DIR="$REPO_ROOT/outputs"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cloudfront-url) CLOUDFRONT_URL="$2"; shift 2 ;;
    --outputs-dir) OUTPUTS_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--cloudfront-url <url>] [--outputs-dir <path>]"
      echo ""
      echo "Packages index.html into a zip for GitHub Pages deployment."
      echo ""
      echo "Without --cloudfront-url, CSV files from outputs/ are bundled into"
      echo "the zip under data/ with a generated manifest.json, so the app"
      echo "works fully standalone."
      echo ""
      echo "With --cloudfront-url, no CSV data is bundled - the app fetches"
      echo "data from CloudFront at runtime."
      echo ""
      echo "Options:"
      echo "  --cloudfront-url   CloudFront distribution URL (from stack output)."
      echo "                     Replaces the placeholder in index.html."
      echo "                     When set, local CSV data is NOT bundled."
      echo "  --outputs-dir      Directory containing CSV files (default: outputs/)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ ! -f "$INDEX_SRC" ]]; then
  echo "Error: index.html not found at $INDEX_SRC"
  exit 1
fi

# Clean previous artifacts
rm -rf "$OUT_DIR" "$OUT_ZIP"
mkdir -p "$OUT_DIR"

# Copy index.html
cp "$INDEX_SRC" "$OUT_DIR/index.html"

if [[ -n "$CLOUDFRONT_URL" ]]; then
  # CloudFront mode: just index.html with the URL baked in.
  [[ "$CLOUDFRONT_URL" != */ ]] && CLOUDFRONT_URL="${CLOUDFRONT_URL}/"
  sed -i.bak "s|https://XXXXXXXXXX.cloudfront.net/|${CLOUDFRONT_URL}|g" "$OUT_DIR/index.html"
  rm -f "$OUT_DIR/index.html.bak"
  echo "Mode: CloudFront"
  echo "CloudFront URL set to: $CLOUDFRONT_URL"
else
  # Self-contained mode: bundle CSVs + manifest into data/.
  if [[ ! -d "$OUTPUTS_DIR" ]]; then
    echo "Error: outputs directory not found at $OUTPUTS_DIR"
    echo "Either provide CSVs in outputs/ or use --cloudfront-url"
    exit 1
  fi

  CSV_COUNT=$(find "$OUTPUTS_DIR" -maxdepth 1 -name '*.csv' | wc -l | tr -d ' ')
  if [[ "$CSV_COUNT" -eq 0 ]]; then
    echo "Error: no CSV files found in $OUTPUTS_DIR"
    exit 1
  fi

  mkdir -p "$OUT_DIR/data"
  cp "$OUTPUTS_DIR"/*.csv "$OUT_DIR/data/"

  RUNS=()
  for f in "$OUT_DIR"/data/*_summary.csv; do
    [[ -f "$f" ]] || continue
    base=$(basename "$f")
    RUNS+=("${base%_summary.csv}")
  done

  if [[ ${#RUNS[@]} -eq 0 ]]; then
    echo "Error: no *_summary.csv files found in $OUTPUTS_DIR"
    rm -rf "$OUT_DIR"
    exit 1
  fi

  JSON_ARRAY=$(printf '%s\n' "${RUNS[@]}" | sort | python3 -c "
import sys, json
runs = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps({'files': runs}))
")
  echo "$JSON_ARRAY" > "$OUT_DIR/data/manifest.json"

  echo "Mode: self-contained (local data)"
  echo "Bundled ${#RUNS[@]} eval run(s): ${RUNS[*]}"
  echo "Bundled $CSV_COUNT CSV file(s) total"
fi

# Create zip with files at archive root.
(cd "$OUT_DIR" && zip -r "$OUT_ZIP" .)
rm -rf "$OUT_DIR"

echo ""
echo "Created: gh-pages-deploy.zip"
echo ""
echo "Ready for GitHub Pages publishing."
