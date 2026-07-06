#!/usr/bin/env bash
# run-daily-leads.sh — Daily lead generation pipeline with Obsidian storage
set -euo pipefail

LEADGEN_DIR="$HOME/.openclaw/workspace/MarvelUs-lead-gen"
VAULT_DIR="$HOME/Obsidian/Penelopi/Leads"
VENV="$LEADGEN_DIR/.venv/bin/activate"
DATE=$(date +%Y-%m-%d)

cd "$LEADGEN_DIR"

if [ -f "$VENV" ]; then
    source "$VENV"
fi

mkdir -p "$VAULT_DIR/By-Category" "$VAULT_DIR/Master"

# Categories to rotate through
CATEGORIES=("plumbers" "electricians" "dentists" "hvac" "locksmiths" "roofers" "cleaning" "auto repair" "pest control")

# Pick category based on day of week
DAY_OF_WEEK=$(date +%w)
CATEGORY_INDEX=$((DAY_OF_WEEK % ${#CATEGORIES[@]}))
TODAY_CATEGORY="${CATEGORIES[$CATEGORY_INDEX]}"

LOCATION="Melbourne, Australia"
LIMIT="10"

LOG_FILE="$LEADGEN_DIR/logs/daily-run-$DATE.log"
mkdir -p "$LEADGEN_DIR/logs"

# Run pipeline silently, capture only summary
SUMMARY=$(bash scripts/run-browser-pipeline.sh "$TODAY_CATEGORY" "$LOCATION" "$LIMIT" 2>&1)

# Copy to Obsidian vault
cp "data/reports/hot_leads.csv" "$VAULT_DIR/By-Category/hot_${TODAY_CATEGORY}_${DATE}.csv"
cp "data/reports/outreach_ready.csv" "$VAULT_DIR/By-Category/all_${TODAY_CATEGORY}_${DATE}.csv"

# Append to master
cat "data/reports/hot_leads.csv" >> "$VAULT_DIR/Master/hot_leads_master.csv"

# Deduplicate master
python3 -c "
import csv
from pathlib import Path

master = Path('$VAULT_DIR/Master/hot_leads_master.csv')
if not master.exists():
    exit()

seen = set()
unique = []
with master.open() as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = row.get('name','') + '|' + row.get('email','') + '|' + row.get('website','')
        if key not in seen:
            seen.add(key)
            unique.append(row)

if unique:
    with master.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=unique[0].keys())
        writer.writeheader()
        writer.writerows(unique)

print(f'📊 Master: {len(unique)} unique leads')
"

# Rich formatted daily report
MASTER_COUNT=$(python3 -c "
import csv
from pathlib import Path
master = Path('$VAULT_DIR/Master/hot_leads_master.csv')
if not master.exists():
    print('0')
    exit()
count = sum(1 for _ in csv.DictReader(master.open()))
print(count)
")

echo "🎯 *Daily Lead Gen: ${TODAY_CATEGORY^}*

$SUMMARY

📊 *Master List:* ${MASTER_COUNT} unique leads
📁 *Files saved to Obsidian*"
