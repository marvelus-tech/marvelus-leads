#!/usr/bin/env python3
"""Generate GitHub Pages dashboard JSON from Obsidian lead CSV exports."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

LEADS_DIR = Path.home() / "Obsidian/Penelopi/Leads/By-Category"
OUTPUT_JSON = Path(__file__).resolve().parents[1] / "dashboard_data.json"

DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.csv$")


def parse_bool(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def parse_score(v: object) -> int:
    try:
        return int(float(str(v).strip()))
    except Exception:
        return 0


def priority_from_score(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def extract_date(path: Path) -> str:
    m = DATE_RE.search(path.name)
    if not m:
        return "1970-01-01"
    return m.group(1)


def generate_sms(name: str, category: str, location: str) -> str:
    short_name = name.split()[0] if name else "there"
    return f"Hi {short_name}, I help {category} in {location} stop missing calls with a natural AI receptionist that books 24/7. Quick 10-min look? [Your Name] Marvelus"


def generate_email_subject(category: str, location: str) -> str:
    return f"AI receptionist for {category} in {location} (24/7 booking)"


def generate_email_body(name: str, category: str, location: str) -> str:
    return f"""Hi {name},

I help {category} businesses in {location} get more bookings with a natural Australian AI receptionist that answers 24/7 and books clients straight into your calendar.

Would you be open to a quick 10-min chat this week?

Best,
[Your Name]
Marvelus"""


def generate_score_reasons(row: dict) -> str:
    reasons = []
    if parse_bool(row.get("needs_ai_voice")):
        reasons.append("No AI chatbot")
    if parse_bool(row.get("needs_call_button")):
        reasons.append("No click-to-call")
    if parse_bool(row.get("needs_web_presence")):
        reasons.append("Weak web presence")
    if parse_bool(row.get("needs_reputation_mgmt")):
        reasons.append("Reputation gaps")
    if row.get("website"):
        reasons.append("Website found")
    if row.get("phone"):
        reasons.append("Phone found")
    if not reasons:
        reasons.append("General opportunity")
    return " | ".join(reasons)


def recommended_from_needs(row: dict) -> str:
    if parse_bool(row.get("needs_ai_voice")):
        return "AI Voice"
    if parse_bool(row.get("needs_web_presence")):
        return "Web Presence"
    if parse_bool(row.get("needs_reputation_mgmt")):
        return "Reputation"
    if parse_bool(row.get("needs_call_button")):
        return "Call Button"
    return "General"


def seo_from_opportunities(row: dict) -> int:
    # Lower tech score = more opportunity.
    score = 50
    if parse_bool(row.get("needs_web_presence")):
        score -= 15
    if parse_bool(row.get("needs_call_button")):
        score -= 10
    if parse_bool(row.get("needs_ai_voice")):
        score -= 10
    if parse_bool(row.get("needs_reputation_mgmt")):
        score -= 5
    if not row.get("website"):
        score -= 10
    return max(10, min(95, score))


def load_leads() -> list[dict]:
    rows: list[dict] = []
    files = sorted(LEADS_DIR.glob("all_*.csv"))
    for f in files:
        run_date = extract_date(f)
        with f.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for r in reader:
                row = dict(r)
                row["run_date"] = run_date
                row["score"] = parse_score(row.get("ai_service_score"))
                row["priority_label"] = priority_from_score(row["score"])
                rows.append(row)
    # dedupe by strongest key, keeping latest run_date then highest score
    dedup: dict[str, dict] = {}
    for r in rows:
        key = "|".join(
            [
                (r.get("name") or "").strip().lower(),
                (r.get("website") or "").strip().lower(),
                (r.get("phone") or "").strip().lower(),
            ]
        )
        prev = dedup.get(key)
        if not prev:
            dedup[key] = r
            continue
        if (r["run_date"], r["score"]) >= (prev["run_date"], prev["score"]):
            dedup[key] = r
    return list(dedup.values())


def render_json(leads: list[dict]) -> str:
    out: list[dict] = []
    for idx, r in enumerate(leads, start=1):
        name = (r.get("name") or "").strip()
        category = (r.get("category") or "business").strip().lower()
        location = (r.get("location") or "Melbourne").strip()
        # simplify location to just city
        if "," in location:
            location = location.split(",")[0].strip()
        website = (r.get("website") or "").strip()
        phone = (r.get("phone") or "").strip()
        email = (r.get("email") or "").strip() or None
        score = r["score"]
        seo = seo_from_opportunities(r)
        recommended = recommended_from_needs(r)
        priority = r["priority_label"]
        score_reasons = generate_score_reasons(r)
        sms = generate_sms(name, category, location)
        email_subject = generate_email_subject(category, location)
        email_body = generate_email_body(name, category, location)
        out.append(
            {
                "id": idx,
                "name": name,
                "category": category,
                "location": location,
                "website": website or None,
                "seo": seo,
                "overall": score,
                "recommended": recommended,
                "priority": priority,
                "multi": False,
                "phone": phone or None,
                "email": email,
                "sms": sms,
                "email_subject": email_subject,
                "email_body": email_body,
                "score_reasons": score_reasons,
            }
        )
    return json.dumps(out, indent=2, ensure_ascii=False)


def main() -> int:
    if not LEADS_DIR.exists():
        raise SystemExit(f"Leads dir not found: {LEADS_DIR}")
    leads = load_leads()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(render_json(leads), encoding="utf-8")
    print(f"Generated {OUTPUT_JSON} ({len(leads)} deduped leads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
