#!/bin/bash
# run-playwright-scraper.sh — Playwright-based Maps Scraper (No Vision Needed)
# Usage: ./run-playwright-scraper.sh "category" "location" [limit]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEADGEN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$LEADGEN_DIR/.venv/bin/activate"

# Default values
CATEGORY="${1:-mechanics}"
LOCATION="${2:-Victoria, Australia}"
LIMIT="${3:-10}"

cd "$LEADGEN_DIR"

# Activate venv if it exists
if [ -f "$VENV" ]; then
    source "$VENV"
fi

# Ensure directories exist
mkdir -p data/processed data/reports

echo "========================================"
echo "Playwright Maps Scraper (No Vision)"
echo "Category: $CATEGORY"
echo "Location: $LOCATION"
echo "Limit: $LIMIT"
echo "========================================"

python3 src/playwright_maps_scraper.py "$CATEGORY" "$LOCATION" --limit "$LIMIT"

echo "Done. Check data/processed/ for results."
