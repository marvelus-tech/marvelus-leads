#!/bin/bash
# quick-lead-scrape.sh — Manual lead scraper with automatic fallback
# Usage: ./quick-lead-scrape.sh [category] [location] [limit]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEADGEN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$LEADGEN_DIR/.venv/bin/activate"

CATEGORY="${1:-$(cd "$LEADGEN_DIR" && python3 src/category_rotator.py)}"
LOCATION="${2:-Victoria, Australia}"
LIMIT="${3:-10}"

cd "$LEADGEN_DIR"

# Activate venv if it exists
if [ -f "$VENV" ]; then
    source "$VENV"
fi

echo "========================================"
echo "Quick Lead Scraper"
echo "Category: $CATEGORY"
echo "Location: $LOCATION"
echo "Limit: $LIMIT"
echo "========================================"

# Try Peekaboo first
echo ""
echo "🎯 Attempt 1: Peekaboo vision scraper..."
if python3 src/peekaboo_maps_agent.py "$CATEGORY" "$LOCATION" --limit "$LIMIT" 2>/dev/null; then
    echo "✅ Peekaboo succeeded!"
    exit 0
else
    echo "❌ Peekaboo failed (likely TCC permission)"
fi

# Fallback to Playwright
echo ""
echo "🔄 Attempt 2: Playwright scraper (no vision needed)..."
python3 src/playwright_maps_scraper.py "$CATEGORY" "$LOCATION" --limit "$LIMIT"

echo ""
echo "Done. Check data/processed/ for results."
