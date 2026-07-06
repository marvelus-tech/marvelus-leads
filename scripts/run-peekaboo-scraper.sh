# run-peekaboo-scraper.sh — Wrapper for Peekaboo Maps Scraper
# Usage: ./run-peekaboo-scraper.sh "category" "location"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEADGEN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$LEADGEN_DIR/.venv/bin/activate"

# Default values — Victoria, Australia, service businesses only
CATEGORY="${1:-$(python3 src/category_rotator.py)}"
LOCATION="${2:-Victoria, Australia}"
LIMIT="${3:-10}"
DELAY="${4:-5}"

# Activate venv if it exists
if [ -f "$VENV" ]; then
    source "$VENV"
fi

cd "$LEADGEN_DIR"

# Ensure directories exist
mkdir -p data/processed data/reports data/debug/peekaboo

# Run the scraper
echo "========================================"
echo "Peekaboo Maps Scraper"
echo "Category: $CATEGORY"
echo "Location: $LOCATION"
echo "Limit: $LIMIT"
echo "========================================"

python3 src/peekaboo_scraper.py "$CATEGORY" "$LOCATION" --limit "$LIMIT" --delay "$DELAY"

echo "Done. Check data/processed/ for results."
