#!/usr/bin/env bash
# run-browser-pipeline.sh — Full pipeline with browser scraper + contact enrichment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEADGEN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$LEADGEN_DIR/.venv/bin/activate"

# Default values
CATEGORY="${1:-plumbers}"
LOCATION="${2:-Melbourne, Australia}"
LIMIT="${3:-5}"

cd "$LEADGEN_DIR"

# Activate venv if it exists
if [ -f "$VENV" ]; then
    source "$VENV"
fi

mkdir -p data/processed data/reports data/debug/browser

# Step 1: Browser scrape (with website extraction)
python3 -c "
import sys, json
sys.path.insert(0, 'src')
from browser_scraper import BrowserMapsScraper, browser_search_with_retry

scraper = BrowserMapsScraper(headless=True, slow_mo=3000, max_results_per_search=$LIMIT, search_delay_seconds=5)
leads = browser_search_with_retry(scraper, '$CATEGORY', '$LOCATION', max_retries=2)

# Save
out = 'data/processed/browser_raw.json'
with open(out, 'w') as f:
    json.dump(leads, f, indent=2, default=str)
print(f'Found {len(leads)} leads')
"

# Step 2: Contact enrichment
python3 -c "
import sys, json
sys.path.insert(0, 'src')
from contact_enricher import enrich_leads_file
enrich_leads_file('data/processed/browser_raw.json', 'data/processed/browser_enriched.json')
"

# Step 3: Intelligence Scoring (Phase 3)
python3 -c "
import sys, json
sys.path.insert(0, 'src')
from intelligence_scorer import enrich_with_intelligence

with open('data/processed/browser_enriched.json') as f:
    leads = json.load(f)

scored = enrich_with_intelligence(leads)

hot = [l for l in scored if l.get('priority') == 'hot']
warm = [l for l in scored if l.get('priority') == 'warm']
cold = [l for l in scored if l.get('priority') == 'cold']

# One-line summary with rich formatting
print(f"🎯 *Lead Gen Results: {CATEGORY.title()}*\n")
print(f"🔥 *Hot:* {len(hot)} | 🌡️ *Warm:* {len(warm)} | ❄️ *Cold:* {len(cold)} | 📊 *Total:* {len(scored)}")

# Save
out = 'data/processed/browser_scored.json'
with open(out, 'w') as f:
    json.dump(scored, f, indent=2, default=str)
"

# Step 4: Generate outreach CSVs by priority
python3 -c "
import json, csv
from pathlib import Path

with open('data/processed/browser_scored.json') as f:
    leads = json.load(f)

all_csv = Path('data/reports/outreach_ready.csv')
hot_csv = Path('data/reports/hot_leads.csv')
warm_csv = Path('data/reports/warm_leads.csv')

fields = ['name', 'email', 'website', 'phone', 'address', 'category', 'location', 
          'contact_confidence', 'priority', 'ai_service_score', 'needs_ai_voice',
          'needs_web_presence', 'needs_reputation_mgmt', 'needs_call_button',
          'rating', 'reviews', 'opportunities']

def write_csv(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for l in data:
            writer.writerow({k: l.get(k, '') for k in fields})

write_csv(all_csv, leads)
write_csv(hot_csv, [l for l in leads if l.get('priority') == 'hot'])
write_csv(warm_csv, [l for l in leads if l.get('priority') == 'warm'])

hot_count = sum(1 for l in leads if l.get('priority') == 'hot')
warm_count = sum(1 for l in leads if l.get('priority') == 'warm')

print(f"📁 *CSV Files*\n• All: {len(leads)}\n• Hot: {hot_count}\n• Warm: {warm_count}")
"
