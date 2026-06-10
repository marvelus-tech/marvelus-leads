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
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    if [[ "$CHANGED" == "1" ]]; then
      MSG="✅ Marvelus Leads dashboard updated: $PAGES_URL"
    else
      MSG="ℹ️ Marvelus Leads dashboard checked (no content changes): $PAGES_URL"
    fi
    curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${MSG}" >/dev/null
    log "Telegram notification sent"
  else
    log "Skipping Telegram (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set)"
  fi
fi

log "Done. Dashboard: $PAGES_URL"
