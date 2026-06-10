#!/usr/bin/env python3
"""Generate GitHub Pages dashboard from Obsidian lead CSV exports."""

from __future__ import annotations

import csv
import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

LEADS_DIR = Path.home() / "Obsidian/Penelopi/Leads/By-Category"
OUTPUT_HTML = Path(__file__).resolve().parents[1] / "index.html"


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
        return "Hot"
    if score >= 50:
        return "Warm"
    return "Cold"


def extract_date(path: Path) -> str:
    m = DATE_RE.search(path.name)
    if not m:
        return "1970-01-01"
    return m.group(1)


def missing_signals(row: dict) -> list[str]:
    mapping = [
        ("needs_ai_voice", "AI voice"),
        ("needs_web_presence", "Web presence"),
        ("needs_reputation_mgmt", "Reputation"),
        ("needs_call_button", "Call button"),
    ]
    out = [label for key, label in mapping if parse_bool(row.get(key))]
    if not row.get("website"):
        out.append("Website")
    if not row.get("email"):
        out.append("Email")
    return out


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
                row["missing_signals"] = missing_signals(row)
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


def esc(v: object) -> str:
    return html.escape(str(v or ""))


def render(leads: list[dict]) -> str:
    total = len(leads)
    hot = sum(1 for x in leads if x["score"] >= 75)
    warm = sum(1 for x in leads if 50 <= x["score"] <= 74)
    categories = Counter((x.get("category") or "unknown").strip().lower() for x in leads)
    category_html = "".join(
        f'<div class="chip"><span>{esc(k.title())}</span><b>{v}</b></div>'
        for k, v in categories.most_common()
    )

    recent = sorted(leads, key=lambda x: (x["run_date"], x["score"]), reverse=True)[:50]
    rows_html = ""
    for r in recent:
        miss = ", ".join(r["missing_signals"]) or "-"
        pri = r["priority_label"]
        pri_cls = pri.lower()
        rows_html += (
            "<tr>"
            f"<td>{esc(r.get('name') or '-')}</td>"
            f"<td>{r['score']}</td>"
            f"<td><span class='pill {pri_cls}'>{pri}</span></td>"
            f"<td>{esc(r.get('category') or '-')}</td>"
            f"<td>{esc(miss)}</td>"
            f"<td>{esc(r.get('run_date'))}</td>"
            "</tr>"
        )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Marvelus Leads Dashboard</title>
  <style>
    :root {{ --bg:#0b1020; --card:#131a2f; --text:#e8edff; --muted:#9aa6cf; --line:#273155; --hot:#ff5470; --warm:#ffb454; --cold:#5b8cff; }}
    *{{box-sizing:border-box}} body{{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:20px}}
    h1{{font-size:28px;margin:0 0 8px}} .sub{{color:var(--muted);margin-bottom:16px}}
    .stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:12px}}
    .card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
    .label{{color:var(--muted);font-size:12px}} .num{{font-size:28px;font-weight:700}}
    .chips{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 18px}}
    .chip{{display:flex;gap:8px;align-items:center;background:var(--card);border:1px solid var(--line);padding:6px 10px;border-radius:999px;color:var(--muted)}}
    .chip b{{color:var(--text)}}
    table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:block}}
    thead,tbody{{display:table;width:100%;table-layout:fixed}}
    tbody{{max-height:65vh;overflow:auto;display:block}}
    th,td{{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
    th{{font-size:12px;color:var(--muted);position:sticky;top:0;background:var(--card)}}
    .pill{{padding:3px 8px;border-radius:999px;font-size:12px;font-weight:600}}
    .hot{{background:rgba(255,84,112,.15);color:#ff8aa0}} .warm{{background:rgba(255,180,84,.15);color:#ffc979}} .cold{{background:rgba(91,140,255,.15);color:#95b6ff}}
    @media (max-width:800px){{.stats{{grid-template-columns:1fr}} table{{font-size:12px}} th:nth-child(4),td:nth-child(4),th:nth-child(6),td:nth-child(6){{display:none}}}}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Marvelus Leads Dashboard</h1>
    <div class=\"sub\">Generated {esc(generated)} • Source: ~/Obsidian/Penelopi/Leads/By-Category/all_*.csv</div>
    <div class=\"stats\">
      <div class=\"card\"><div class=\"label\">Total Leads</div><div class=\"num\">{total}</div></div>
      <div class=\"card\"><div class=\"label\">Hot (75+)</div><div class=\"num\">{hot}</div></div>
      <div class=\"card\"><div class=\"label\">Warm (50-74)</div><div class=\"num\">{warm}</div></div>
    </div>
    <div class=\"chips\">{category_html}</div>
    <table>
      <thead><tr><th>Business</th><th>Score</th><th>Priority</th><th>Category</th><th>Missing Signals</th><th>Date</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> int:
    if not LEADS_DIR.exists():
        raise SystemExit(f"Leads dir not found: {LEADS_DIR}")
    leads = load_leads()
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(render(leads), encoding="utf-8")
    print(f"Generated {OUTPUT_HTML} ({len(leads)} deduped leads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
