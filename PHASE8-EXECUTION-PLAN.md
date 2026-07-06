# Marvelus Leads — Phase 8 Execution Plan
## Cannes Lions-Grade Digital Experience Architecture

**Date:** 2026-07-06
**Project:** https://marvelus-tech.github.io/marvelus-leads/
**Lead Creative Director:** OpenClaw (Wieden+Kennedy Interactive Division)

---

## Vision Statement

Transform the Marvelus Leads dashboard from a functional lead tracker into a **culture-defining, self-contained sales intelligence platform** — the kind of tool that makes a prospecting agency look like they have a team of 20 analysts. Every interaction must feel inevitable, every report must feel like it cost $5,000 to produce, and every prospect must feel like they already lost by not hiring us.

---

## PHASE 1: Foundation — Prospecting Scraper Engine
**Duration:** 1 session
**Priority:** CRITICAL (unblocks everything else)
**Dependencies:** None

### 1.1 Melbourne Suburb Scraper (`scripts/melbourne_prospector.py`)
**Objective:** Automate the discovery of unoptimized Melbourne businesses in target suburbs.

**Deliverables:**
- `scripts/melbourne_prospector.py` — Command-line tool
- Input: service type (e.g., "plumber"), suburb (e.g., "Frankston"), depth (pages to scan)
- Output: `prospects_raw.json` with business name, address, phone, website, GBP link, review count, rating, estimated Google position
- Scoring: auto-calculates opportunity score (0-100) based on signals from the strategy doc
- Export: CSV compatible with existing dashboard pipeline

**Technical approach:**
- Google Maps API or SERP scraping via `requests` + `BeautifulSoup`
- Review extraction from GBP URLs
- Position estimation via SERP ranking
- Opportunity scoring using the 10-point checklist from `melbourne-seo-client-strategy.md`

**Checkpoint:**
- [ ] Run `python scripts/melbourne_prospector.py --service plumber --suburb Frankston --pages 3`
- [ ] Verify output CSV has ≥10 valid prospects with scores
- [ ] Import into dashboard and verify rendering

**Risk:** Google rate-limiting. **Mitigation:** Add delays, use rotating user agents, cache results.

---

## PHASE 2: The Audit Report Template — "The $5K Page"
**Duration:** 1-2 sessions
**Priority:** HIGH (core value proposition)
**Dependencies:** Phase 1 complete (real prospect data to template against)

### 2.1 HTML/CSS Audit Report Template (`audit-report-template.html`)
**Objective:** A single-page, print-ready, brand-aligned audit report that looks like it was designed by Pentagram.

**Deliverables:**
- `audit-report-template.html` — Standalone template in the repo
- Sections:
  - **Hero:** Business name + suburb + "SEO Opportunity Report" + Marvelus branding
  - **Executive Summary:** 3-4 sentences with current status + expected outcome
  - **Score Card:** Circular progress indicators for Technical (0-100), On-Page (0-100), Local (0-100), Overall (0-100)
  - **Current Status:** ✅ What's Working / ❌ What's Broken / ⚠️ What's Missing
  - **The Competition:** Top 3 competitors with mini-cards showing their position, reviews, rating
  - **Top 5 Quick Wins:** Prioritized table with Issue | Impact | Time to Fix
  - **90-Day Roadmap:** Visual timeline with 3 phases (Foundation → Content → Scale)
  - **Expected Results:** Month 1/2/3 metrics table
  - **CTA:** "Schedule a Free Strategy Call" with Calendly-style booking prompt

**Design specs:**
- Same Mercury design language as the dashboard (DM Sans, white cards, subtle shadows, accent gradients)
- Print-friendly CSS (`@media print` optimized)
- Exportable to PDF via browser print or `puppeteer`/`weasyprint`
- Responsive for mobile viewing

**Checkpoint:**
- [ ] Template renders cleanly in browser
- [ ] Print-to-PDF produces professional 1-page output
- [ ] All sections populated with real data from a test prospect
- [ ] User reviews and approves the visual design

**Risk:** PDF generation complexity. **Mitigation:** Start with browser print, add server-side generation later if needed.

---

## PHASE 3: The Audit Automation Engine
**Duration:** 1-2 sessions
**Priority:** HIGH (multiplier on productivity)
**Dependencies:** Phase 1 (scraper), Phase 2 (template)

### 3.1 Python Audit Automator (`scripts/audit_automator.py`)
**Objective:** Enter a business name. Get a full audit report in 30 seconds.

**Deliverables:**
- `scripts/audit_automator.py` — Command-line tool
- Input: `python scripts/audit_automator.py --name "Joe's Plumbing" --suburb "Frankston" --service "plumber"`
- What it does:
  1. Calls the prospector to find the business (or uses provided URL)
  2. Runs technical checks: SSL, mobile-friendly, PageSpeed, Core Web Vitals, indexing, schema
  3. Runs on-page analysis: title, meta, H1, content length, keyword usage, alt text, internal links
  4. Runs local SEO analysis: GBP claimed, reviews, rating, photos, posts, NAP consistency
  5. Finds top 3 competitors and analyzes their positions
  6. Scores everything (0-100 per category)
  7. Generates prioritized quick wins
  8. Populates the HTML template from Phase 2
  9. Outputs: `reports/[business-name]-audit-report.html` + `[business-name]-audit-report.pdf` (optional)

**Technical approach:**
- `requests` + `BeautifulSoup` for on-page scraping
- `pagespeed-insights` API or `lighthouse` CLI for speed scores
- `googlesearch-python` or SERP scraping for competitor positions
- Jinja2 templating for report generation
- `weasyprint` or `pdfkit` for PDF export

**Checkpoint:**
- [ ] Run on 3 real Melbourne businesses
- [ ] Verify technical scores match manual checks
- [ ] Verify competitor analysis is accurate
- [ ] Report renders correctly in browser and prints to PDF
- [ ] User can run end-to-end in <60 seconds

**Risk:** External API dependencies (PageSpeed API). **Mitigation:** Cache responses, fallback to manual checks if API fails.

---

## PHASE 4: The Slide-Out Prospect Tracker
**Duration:** 1-2 sessions
**Priority:** MEDIUM-HIGH (dashboard enhancement, user-facing)
**Dependencies:** Phase 1 (scraper data format known), Phase 3 (audit scores known)

### 4.1 Slide-Out Tracker Sheet in Dashboard
**Objective:** A dedicated prospecting workspace that slides out from the right, with formulas to score and prioritize prospects — right next to the Sales Playbook.

**Deliverables:**
- Button in the dashboard header: 📊 "Prospect Tracker" (right of the Playbook button)
- Slide-out panel (same animation as Playbook) containing:
  - **Import Section:** Paste CSV or click "Run Scraper" to populate from Phase 1
  - **Prospect Table:** Sortable columns:
    - Business Name
    - Suburb
    - Service
    - Opportunity Score (0-100, auto-calculated)
    - Tech Score (0-100)
    - Local Score (0-100)
    - Review Count
    - Rating
    - Website? (Y/N)
    - SSL? (Y/N)
    - GBP Claimed? (Y/N)
    - Priority (🔥 Hot / 🌡 Warm / ❄ Cold)
    - Status (New / Contacted / Audit Sent / Meeting Booked / Closed / Lost)
    - Actions: 📝 Generate Audit | 📧 Copy Outreach | ⭐ Add to Pipeline
  - **Formula Bar:** Live stats at the bottom
    - Total Prospects: X
    - Hot: X | Warm: X | Cold: X
    - Audits Sent: X | Meetings: X | Closed: X
    - Pipeline Value: $X (uses estimated client values from strategy doc)
  - **Scoring Formula:**
    - Base: 100
    - No website: +25
    - No SSL: +15
    - <10 reviews: +15
    - <4.0 rating: +10
    - No GBP claimed: +20
    - No GBP posts in 30 days: +5
    - No photos: +5
    - On page 2+ of SERP: +10
    - Max score: 100 (cap)

**Technical approach:**
- Pure HTML/CSS/JS in `index.html` (same slide-out pattern as Playbook)
- Data stored in `localStorage` (separate key from leads: `prospectTrackerData`)
- CSV import/export functionality
- "Add to Pipeline" button pushes prospect into the main leads grid with a flag `prospect: true`

**Checkpoint:**
- [ ] Slide-out opens/closes smoothly
- [ ] Table renders 10+ test prospects
- [ ] Scoring formulas calculate correctly
- [ ] Status changes persist in localStorage
- [ ] "Add to Pipeline" successfully adds to main leads grid
- [ ] User can import/export CSV

**Risk:** localStorage size limits. **Mitigation:** Compress data, warn at >500 prospects, offer export.

---

## PHASE 5: Integration & Polish
**Duration:** 1 session
**Priority:** MEDIUM (ties everything together)
**Dependencies:** Phases 1-4 complete

### 5.1 Dashboard Integration
- **Audit Button on Lead Cards:** Each lead in the main grid gets an "🔍 Audit" button that runs the Phase 3 automator and opens the report in a new tab
- **Prospect Tracker Button:** In the header, next to Playbook
- **Pipeline Integration:** Prospects added from tracker appear in main leads with a "Prospect" badge
- **Streak Update:** Running an audit or adding a prospect counts as an activity for the streak system

### 5.2 Pipeline & Automation Scripts Update
- `run_leads_dashboard_pipeline.sh` updated to also run the prospector for configured niches/suburbs
- `generate_leads_dashboard.py` updated to merge prospect data with existing leads

### 5.3 Documentation
- `README.md` updated with Phase 8 features
- `AUDIT_SYSTEM.md` documenting the audit workflow
- `PROSPECTOR.md` documenting the scraper usage

**Checkpoint:**
- [ ] End-to-end test: scrape → audit → report → track → add to pipeline → contact → close
- [ ] All features work on mobile
- [ ] GitHub Pages deploys successfully
- [ ] User signs off on the complete experience

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google SERP scraping blocked | Medium | High | Rotate agents, add delays, cache aggressively |
| PageSpeed API rate limits | Medium | Medium | Cache responses, fallback to manual checks |
| localStorage full | Low | Medium | Warn user, offer export, compress data |
| Mobile slide-out UX issues | Medium | Medium | Test on real devices, simplify animations |
| Report template too complex | Low | Medium | Start simple, iterate with user feedback |
| Scope creep | High | High | Phase gates, user approval per phase |

---

## Timeline

| Phase | Est. Duration | Cumulative |
|-------|--------------|------------|
| Phase 1: Scraper | 1 session | 1 session |
| Phase 2: Report Template | 1-2 sessions | 2-3 sessions |
| Phase 3: Audit Automator | 1-2 sessions | 3-5 sessions |
| Phase 4: Slide-Out Tracker | 1-2 sessions | 4-7 sessions |
| Phase 5: Integration | 1 session | 5-8 sessions |

---

## Next Step

**Awaiting your approval.** Once approved, I will execute Phase 1 (Prospecting Scraper) first, then present the working scraper for your review before proceeding to Phase 2.
