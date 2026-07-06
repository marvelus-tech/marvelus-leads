#!/usr/bin/env bash
# test-multi-category.sh — Run pipeline on multiple categories and merge results
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEADGEN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$LEADGEN_DIR/.venv/bin/activate"

cd "$LEADGEN_DIR"
if [ -f "$VENV" ]; then
    source "$VENV"
fi

# Categories to test
CATEGORIES=("plumbers" "electricians" "dentists" "hvac")
LOCATION="Melbourne, Australia"
LIMIT="5"

mkdir -p data/processed data/reports

# Clear previous results
cp data/reports/outreach_ready.csv data/reports/outreach_ready.csv.bak 2>/dev/null || true

for CATEGORY in "${CATEGORIES[@]}"; do
    echo ""
    echo "========================================"
    echo "Running: $CATEGORY"
    echo "========================================"
    bash scripts/run-browser-pipeline.sh "$CATEGORY" "$LOCATION" "$LIMIT" 2>&1 | tail -20
    
    # Save category-specific output
    cp data/reports/hot_leads.csv "data/reports/hot_${CATEGORY}.csv" 2>/dev/null || true
done

# Merge all hot leads into one master file
echo ""
echo "========================================"
echo "Merging results..."
echo "========================================"

python3 -c "
import csv
from pathlib import Path

categories = ['plumbers', 'electricians', 'dentists', 'hvac']
all_leads = []

for cat in categories:
    csv_path = Path(f'data/reports/hot_{cat}.csv')
    if csv_path.exists():
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_leads.append(row)

if all_leads:
    master = Path('data/reports/master_hot_leads.csv')
    with master.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_leads[0].keys())
        writer.writeheader()
        writer.writerows(all_leads)
    print(f'Master hot leads: {len(all_leads)} → {master}')
    
    # Print summary
    for l in all_leads[:15]:
        print(f\"  🔥 {l.get('name')[:40]:40} | {l.get('email') or 'NO EMAIL':25} | score={l.get('ai_service_score')}\")
else:
    print('No leads found')
"

echo ""
echo "========================================"
echo "✅ Multi-category test complete!"
echo "========================================"
