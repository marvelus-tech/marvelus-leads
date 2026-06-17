#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$HOME/.openclaw/workspace"
LEADGEN_DIR="$WORKSPACE/leadgen"
REPO_DIR="$WORKSPACE/marvelus-leads"
GENERATOR="$REPO_DIR/scripts/generate_leads_dashboard.py"
PAGES_URL="https://marvelus-tech.github.io/marvelus-leads/"

RUN_SCRAPER="${RUN_SCRAPER:-1}"
PUSH_CHANGES="${PUSH_CHANGES:-1}"
SEND_TELEGRAM="${SEND_TELEGRAM:-1}"

# Optional env file for TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
if [[ -f "$WORKSPACE/.env" ]]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE/.env"
fi

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

log "Syncing latest repo state"
cd "$REPO_DIR"
git pull --rebase origin main || true

if [[ "$RUN_SCRAPER" == "1" ]]; then
  log "Running lead scraper (best-effort)"
  if ! bash "$LEADGEN_DIR/scripts/run-daily-leads.sh"; then
    log "Lead scraper failed; continuing with existing lead files"
  fi
else
  log "Skipping scraper (RUN_SCRAPER=$RUN_SCRAPER)"
fi

log "Generating dashboard HTML"
python3 "$GENERATOR"

log "Preparing git commit"
cd "$REPO_DIR"
git add index.html scripts/generate_leads_dashboard.py scripts/run_leads_dashboard_pipeline.sh

if git diff --cached --quiet; then
  log "No dashboard changes to commit"
  CHANGED=0
else
  CHANGED=1
  git commit -m "Update leads dashboard: $(date +%Y-%m-%d)"
  if [[ "$PUSH_CHANGES" == "1" ]]; then
    git push origin main
    log "Pushed to GitHub"
  else
    log "Skipping push (PUSH_CHANGES=$PUSH_CHANGES)"
  fi
fi

if [[ "$SEND_TELEGRAM" == "1" ]]; then
  # OpenClaw handles Telegram delivery via cron job delivery.mode=announce
  # No bot token needed — uses native channel routing
  if [[ "$CHANGED" == "1" ]]; then
    echo "✅ Dashboard updated: $PAGES_URL"
  else
    echo "ℹ️ Dashboard checked (no changes): $PAGES_URL"
  fi
  log "Telegram notification queued via OpenClaw delivery"
fi

log "Done. Dashboard: $PAGES_URL"
