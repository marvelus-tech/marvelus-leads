#!/usr/bin/env python3
"""
Melbourne Prospector — Phase 1: Prospecting Scraper Engine

Scrapes Google Maps for businesses in a given Melbourne suburb + service,
performs lightweight SEO checks, and scores prospects 0-100 on opportunity.

Usage:
    python3 scripts/melbourne_prospector.py --service plumber --suburb Frankston --pages 3
    python3 scripts/melbourne_prospector.py --service electrician --suburb Essendon --pages 2 --output prospects.csv
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

REQUEST_DELAY = (1.5, 3.5)

OPPORTUNITY_WEIGHTS = {
    "no_website": 20,
    "no_ssl": 12,
    "low_reviews": 10,
    "bad_rating": 10,
    "no_schema": 8,
    "poor_mobile": 8,
    "slow_speed": 8,
    "missing_title": 5,
    "missing_meta": 5,
    "missing_h1": 5,
    "thin_content": 5,
}

MAX_SCORE = 100


# ───────────────────────────────────────────────
# Data Model
# ───────────────────────────────────────────────

@dataclass
class Prospect:
    """A scored business prospect."""

    name: str = ""
    service: str = ""
    suburb: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    gbp_url: str = ""
    rating: float = 0.0
    review_count: int = 0
    has_website: bool = False
    has_ssl: bool = False
    has_schema: bool = False
    has_title: bool = False
    has_meta_desc: bool = False
    has_h1: bool = False
    word_count: int = 0
    mobile_ok: bool = False
    page_speed_score: int = 0
    opportunity_score: int = 0
    priority: str = "Cold"
    status: str = "New"
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "google_maps"
    signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["signals"] = json.dumps(self.signals) if self.signals else ""
        return d


# ───────────────────────────────────────────────
# Google Maps Scraper (Playwright)
# ───────────────────────────────────────────────

def scrape_google_maps(service: str, suburb: str, pages: int = 3) -> List[dict]:
    """
    Scrape Google Maps for businesses matching service + suburb.
    Uses Playwright with stealth to render the page and extract data.
    """
    search_query = f"{service} in {suburb} Victoria Australia"
    results = []

    print(f"🔍 Searching Google Maps: '{search_query}'")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(USER_AGENTS),
            locale="en-AU",
            timezone_id="Australia/Melbourne",
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-AU', 'en'] });
            window.chrome = { runtime: {} };
            delete navigator.__proto__.webdriver;
        """)

        page = context.new_page()
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(60000)

        try:
            # Navigate to Google Maps
            print("  🌐 Loading Google Maps...")
            page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 4))

            # Handle cookie consent
            try:
                cookie_buttons = page.locator('button:has-text("Accept all")').all()
                if cookie_buttons:
                    cookie_buttons[0].click()
                    time.sleep(1)
            except Exception:
                pass

            # Search
            print(f"  🔎 Entering search query...")
            search_box = page.locator('input[name="q"]').first
            search_box.fill(search_query)
            page.locator('button[aria-label="Search"]').first.click()
            
            # Wait for results
            print("  ⏳ Waiting for results to load...")
            time.sleep(random.uniform(5, 7))

            # Collect place links from search results
            collected = set()
            place_links = []
            
            # Find all place links
            links = page.locator('a[href*="/maps/place/"]').all()
            print(f"  📍 Found {len(links)} place links")
            
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    name = link.get_attribute("aria-label") or ""
                    if not name:
                        name = link.inner_text().strip()
                    
                    if not name or name in collected or len(name) < 3:
                        continue
                    collected.add(name)
                    
                    place_links.append({
                        "name": name,
                        "gbp_url": href,
                    })
                except Exception:
                    continue
            
            # Visit each place page to get details
            print(f"  🔍 Visiting {len(place_links)} place pages for details...")
            
            for place in place_links[:pages * 8]:
                try:
                    name = place["name"]
                    gbp_url = place["gbp_url"]
                    
                    # Visit place page
                    page.goto(gbp_url, wait_until="domcontentloaded")
                    time.sleep(random.uniform(2, 3))
                    
                    # Extract details
                    details = {"name": name, "gbp_url": page.url}
                    
                    # Rating and reviews - try to find in page text
                    try:
                        page_text = page.inner_text('body')
                        # Look for pattern like "4.5" followed by review count
                        rating_match = re.search(r'(\d+\.?\d*)\s*\((\d+)\)', page_text)
                        if rating_match:
                            details["rating"] = float(rating_match.group(1))
                            details["review_count"] = int(rating_match.group(2))
                    except Exception:
                        details["rating"] = 0.0
                        details["review_count"] = 0
                    
                    # Website
                    try:
                        website_link = page.locator('a[data-item-id="authority"]').first
                        if website_link.is_visible():
                            details["website"] = website_link.get_attribute("href", "")
                        else:
                            # Try finding any external link
                            links = page.locator('a[href^="http"]').all()
                            for link in links:
                                href = link.get_attribute("href", "")
                                if href and not any(x in href for x in ["google.com", "goo.gl", "maps.google"]):
                                    text = link.inner_text().strip()
                                    if text and len(text) < 50:
                                        details["website"] = href
                                        break
                    except Exception:
                        details["website"] = ""
                    
                    # Address
                    try:
                        addr_el = page.locator('[data-item-id*="address"]').first
                        if addr_el.is_visible():
                            aria = addr_el.get_attribute("aria-label", "")
                            if aria:
                                details["address"] = aria.replace("Address: ", "")
                            else:
                                details["address"] = addr_el.inner_text().strip()
                    except Exception:
                        details["address"] = ""
                    
                    # Phone
                    try:
                        phone_el = page.locator('[data-tooltip="Copy phone number"]').first
                        if phone_el.is_visible():
                            details["phone"] = phone_el.inner_text().strip()
                    except Exception:
                        details["phone"] = ""
                    
                    results.append(details)
                    print(f"  ✅ {name} | {details.get('rating', 0)}★ ({details.get('review_count', 0)} reviews) | {details.get('website', '')}")
                    
                except Exception as e:
                    continue

        except Exception as e:
            print(f"⚠️  Error during scraping: {e}")
        finally:
            browser.close()

    print(f"\n📊 Total businesses collected: {len(results)}")
    return results


# ───────────────────────────────────────────────
# Website SEO Checks
# ───────────────────────────────────────────────

def check_website(url: str) -> dict:
    """
    Perform lightweight SEO checks on a website.
    Returns dict of signals.
    """
    signals = {
        "has_website": False,
        "has_ssl": False,
        "has_title": False,
        "has_meta_desc": False,
        "has_h1": False,
        "word_count": 0,
        "has_schema": False,
        "mobile_ok": False,
        "page_speed_score": 0,
    }

    if not url or not url.startswith("http"):
        return signals

    signals["has_website"] = True

    # Check SSL
    if url.startswith("https://"):
        signals["has_ssl"] = True

    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = soup.find("title")
        signals["has_title"] = bool(title and title.get_text().strip())

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        signals["has_meta_desc"] = bool(meta_desc and meta_desc.get("content", "").strip())

        # H1
        h1 = soup.find("h1")
        signals["has_h1"] = bool(h1 and h1.get_text().strip())

        # Word count (approximate)
        text = soup.get_text(separator=" ", strip=True)
        signals["word_count"] = len(text.split())

        # Schema markup (JSON-LD or microdata)
        schema_scripts = soup.find_all("script", type="application/ld+json")
        schema_attrs = soup.find_all(attrs={"itemscope": True})
        signals["has_schema"] = bool(schema_scripts or schema_attrs)

    except requests.exceptions.SSLError:
        signals["has_website"] = True
        signals["has_ssl"] = False
    except Exception:
        pass

    return signals


# ───────────────────────────────────────────────
# Scoring Engine
# ───────────────────────────────────────────────

def calculate_score(prospect: Prospect) -> int:
    """
    Calculate opportunity score 0-100.
    Higher score = more problems = better opportunity for SEO services.
    """
    score = 0
    signals = {}

    # 1. No website (highest weight)
    if not prospect.has_website:
        score += OPPORTUNITY_WEIGHTS["no_website"]
        signals["no_website"] = True

    # 2. No SSL (if they have a website)
    if prospect.has_website and not prospect.has_ssl:
        score += OPPORTUNITY_WEIGHTS["no_ssl"]
        signals["no_ssl"] = True

    # 3. Low reviews (< 10)
    if prospect.review_count < 10:
        score += OPPORTUNITY_WEIGHTS["low_reviews"]
        signals["low_reviews"] = True

    # 4. Bad rating (< 4.0)
    if prospect.rating > 0 and prospect.rating < 4.0:
        score += OPPORTUNITY_WEIGHTS["bad_rating"]
        signals["bad_rating"] = True

    # 5. No schema markup
    if prospect.has_website and not prospect.has_schema:
        score += OPPORTUNITY_WEIGHTS["no_schema"]
        signals["no_schema"] = True

    # 6. Missing title
    if prospect.has_website and not prospect.has_title:
        score += OPPORTUNITY_WEIGHTS["missing_title"]
        signals["missing_title"] = True

    # 7. Missing meta description
    if prospect.has_website and not prospect.has_meta_desc:
        score += OPPORTUNITY_WEIGHTS["missing_meta"]
        signals["missing_meta"] = True

    # 8. Missing H1
    if prospect.has_website and not prospect.has_h1:
        score += OPPORTUNITY_WEIGHTS["missing_h1"]
        signals["missing_h1"] = True

    # 9. Thin content (< 300 words)
    if prospect.has_website and prospect.word_count < 300:
        score += OPPORTUNITY_WEIGHTS["thin_content"]
        signals["thin_content"] = True

    # 10. Poor mobile / page speed (proxy)
    if prospect.has_website:
        if not prospect.has_title and not prospect.has_meta_desc:
            score += OPPORTUNITY_WEIGHTS["poor_mobile"]
            signals["poor_mobile_proxy"] = True

    # Cap at 100
    prospect.opportunity_score = min(score, MAX_SCORE)
    prospect.signals = signals

    # Set priority tier
    if prospect.opportunity_score >= 70:
        prospect.priority = "Hot"
    elif prospect.opportunity_score >= 40:
        prospect.priority = "Warm"
    else:
        prospect.priority = "Cold"

    return prospect.opportunity_score


# ───────────────────────────────────────────────
# CSV Output
# ───────────────────────────────────────────────

def write_csv(prospects: List[Prospect], output_path: str) -> None:
    """Write prospects to CSV."""
    if not prospects:
        print("⚠️  No prospects to write.")
        return

    fieldnames = [
        "name", "service", "suburb", "address", "phone", "website",
        "gbp_url", "rating", "review_count", "has_website", "has_ssl",
        "has_schema", "has_title", "has_meta_desc", "has_h1", "word_count",
        "mobile_ok", "page_speed_score", "opportunity_score", "priority",
        "status", "scraped_at", "source", "signals",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in prospects:
            writer.writerow(p.to_dict())

    print(f"\n💾 Wrote {len(prospects)} prospects to {output_path}")


# ───────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Melbourne Prospector — Find and score local business SEO opportunities"
    )
    parser.add_argument("--service", required=True, help="Service type (e.g., plumber, electrician)")
    parser.add_argument("--suburb", required=True, help="Melbourne suburb (e.g., Frankston, Dandenong)")
    parser.add_argument("--pages", type=int, default=3, help="Approximate 'pages' to scroll (default: 3)")
    parser.add_argument("--output", default="prospects_raw.csv", help="Output CSV path")
    parser.add_argument("--no-website-check", action="store_true", help="Skip website SEO checks (faster)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🎯 Melbourne Prospector — Phase 1")
    print(f"{'='*60}")
    print(f"Service: {args.service}")
    print(f"Suburb:  {args.suburb}")
    print(f"Pages:   {args.pages}")
    print(f"Output:  {args.output}")
    print(f"{'='*60}\n")

    # 1. Scrape Google Maps
    raw_businesses = scrape_google_maps(args.service, args.suburb, args.pages)

    if not raw_businesses:
        print("❌ No businesses found. Try different search terms or increase --pages.")
        sys.exit(1)

    # 2. Enrich with website checks + score
    prospects = []
    for biz in raw_businesses:
        p = Prospect(
            name=biz.get("name", ""),
            service=args.service,
            suburb=args.suburb,
            address=biz.get("address", ""),
            phone=biz.get("phone", ""),
            website=biz.get("website", ""),
            gbp_url=biz.get("gbp_url", ""),
            rating=biz.get("rating", 0.0),
            review_count=biz.get("review_count", 0),
        )

        # Website checks
        if not args.no_website_check and p.website:
            print(f"  🔎 Checking website: {p.website}")
            web_signals = check_website(p.website)
            p.has_website = web_signals["has_website"]
            p.has_ssl = web_signals["has_ssl"]
            p.has_title = web_signals["has_title"]
            p.has_meta_desc = web_signals["has_meta_desc"]
            p.has_h1 = web_signals["has_h1"]
            p.word_count = web_signals["word_count"]
            p.has_schema = web_signals["has_schema"]
            p.mobile_ok = web_signals["mobile_ok"]
            p.page_speed_score = web_signals["page_speed_score"]
            time.sleep(random.uniform(*REQUEST_DELAY))
        else:
            p.has_website = bool(p.website)

        # Score
        calculate_score(p)
        prospects.append(p)

        if args.verbose:
            print(f"    → Score: {p.opportunity_score}/100 | Priority: {p.priority}")

    # 3. Sort by score descending
    prospects.sort(key=lambda x: x.opportunity_score, reverse=True)

    # 4. Summary
    hot = sum(1 for p in prospects if p.priority == "Hot")
    warm = sum(1 for p in prospects if p.priority == "Warm")
    cold = sum(1 for p in prospects if p.priority == "Cold")
    no_site = sum(1 for p in prospects if not p.has_website)

    print(f"\n{'='*60}")
    print(f"📊 PROSPECTING SUMMARY")
    print(f"{'='*60}")
    print(f"Total prospects:  {len(prospects)}")
    print(f"🔥 Hot (≥70):      {hot}")
    print(f"🌡️  Warm (40-69):   {warm}")
    print(f"❄️  Cold (<40):     {cold}")
    print(f"🚫 No website:     {no_site}")
    print(f"{'='*60}")

    # 5. Write CSV
    write_csv(prospects, args.output)

    # 6. Top 5 preview
    print(f"\n🏆 Top 5 Opportunities:")
    for i, p in enumerate(prospects[:5], 1):
        print(f"  {i}. {p.name} — {p.opportunity_score}/100 ({p.priority})")
        if p.website:
            print(f"     Website: {p.website}")
        print(f"     Rating: {p.rating}★ ({p.review_count} reviews)")
        print(f"     Signals: {', '.join(p.signals.keys()) if p.signals else 'None'}")


if __name__ == "__main__":
    main()
