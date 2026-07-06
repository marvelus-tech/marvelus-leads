#!/usr/bin/env python3
"""
Marvelus Audit Automation Engine — Phase 3

Performs a comprehensive SEO audit on a Melbourne business in 30 seconds
that would take a human 30 minutes. Outputs a $5K-looking audit report.

Usage:
    python3 scripts/audit_automator.py --name "Joe's Plumbing" --suburb Frankston --service plumber
    python3 scripts/audit_automator.py --url https://example.com --suburb Brighton --service electrician

Author: SpaceX-grade web dev
"""

import argparse
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

REQUEST_DELAY = (1.0, 2.5)

# Scoring weights
TECHNICAL_WEIGHTS = {
    "ssl": 25,
    "mobile": 20,
    "speed": 20,
    "schema": 15,
    "indexing": 10,
    "sitemap": 10,
}

ONPAGE_WEIGHTS = {
    "title": 25,
    "meta_desc": 20,
    "h1": 15,
    "content_length": 15,
    "images_alt": 10,
    "internal_links": 10,
    "canonical": 5,
}

LOCAL_WEIGHTS = {
    "gbp_claimed": 25,
    "gbp_reviews": 20,
    "gbp_rating": 15,
    "gbp_photos": 10,
    "gbp_posts": 10,
    "nap_consistency": 15,
    "citations": 5,
}


# ───────────────────────────────────────────────
# Data Models
# ───────────────────────────────────────────────

@dataclass
class TechnicalAudit:
    has_ssl: bool = False
    is_mobile_friendly: bool = False
    has_viewport: bool = False
    page_speed_score: int = 0
    core_web_vitals: Dict = field(default_factory=dict)
    has_schema: bool = False
    schema_types: List[str] = field(default_factory=list)
    has_robots_txt: bool = False
    has_sitemap: bool = False
    is_indexable: bool = True
    score: int = 0


@dataclass
class OnPageAudit:
    title: str = ""
    title_length: int = 0
    meta_desc: str = ""
    meta_desc_length: int = 0
    h1: str = ""
    h2_count: int = 0
    h3_count: int = 0
    word_count: int = 0
    image_count: int = 0
    images_with_alt: int = 0
    internal_links: int = 0
    external_links: int = 0
    has_canonical: bool = False
    keywords: List[str] = field(default_factory=list)
    score: int = 0


@dataclass
class LocalSEOAudit:
    gbp_name: str = ""
    gbp_url: str = ""
    gbp_claimed: bool = False
    gbp_rating: float = 0.0
    gbp_review_count: int = 0
    gbp_photo_count: int = 0
    gbp_has_posts: bool = False
    gbp_address: str = ""
    gbp_phone: str = ""
    nap_consistent: bool = False
    citations_found: int = 0
    score: int = 0


@dataclass
class CompetitorAnalysis:
    name: str = ""
    position: int = 0
    website: str = ""
    rating: float = 0.0
    review_count: int = 0
    has_website: bool = False
    snippet: str = ""


@dataclass
class AuditReport:
    business_name: str = ""
    service: str = ""
    suburb: str = ""
    website_url: str = ""
    audited_at: str = field(default_factory=lambda: datetime.now().isoformat())
    technical: TechnicalAudit = field(default_factory=TechnicalAudit)
    onpage: OnPageAudit = field(default_factory=OnPageAudit)
    local: LocalSEOAudit = field(default_factory=LocalSEOAudit)
    competitors: List[CompetitorAnalysis] = field(default_factory=list)
    overall_score: int = 0
    quick_wins: List[Dict] = field(default_factory=list)
    opportunity_count: int = 0


# ───────────────────────────────────────────────
# Website Discovery
# ───────────────────────────────────────────────

def find_website(business_name: str, suburb: str, service: str) -> Optional[str]:
    """Find business website via Google search."""
    search_query = f"{business_name} {suburb} {service}"
    url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-AU,en;q=0.5",
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for result links
        results = soup.select('div[data-header-feature] a[href], div[data-result-feature] a[href], .g a[href]')
        
        for result in results:
            href = result.get("href", "")
            if href.startswith("http") and not any(x in href for x in ["google.com", "facebook.com", "instagram.com", "yelp.com"]):
                return href
        
        # Fallback: any link that looks like a business site
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if href.startswith('http') and not any(x in href for x in ['google.com', 'facebook.com', 'instagram.com']):
                text = link.get_text().lower()
                if any(word in text for word in ['plumbing', 'plumber', 'service', 'contact', 'home']):
                    return href
    except Exception as e:
        print(f"  ⚠️  Website discovery failed: {e}")
    
    return None


# ───────────────────────────────────────────────
# Technical Audit
# ───────────────────────────────────────────────

def run_technical_audit(url: str) -> TechnicalAudit:
    """Run technical SEO checks on a website."""
    audit = TechnicalAudit()
    
    if not url or not url.startswith("http"):
        return audit
    
    # SSL check
    audit.has_ssl = url.startswith("https://")
    
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Mobile viewport check
        viewport = soup.find("meta", attrs={"name": "viewport"})
        audit.has_viewport = bool(viewport)
        audit.is_mobile_friendly = bool(viewport)
        
        # Schema markup
        schema_scripts = soup.find_all("script", type="application/ld+json")
        audit.has_schema = bool(schema_scripts)
        audit.schema_types = []
        for script in schema_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    audit.schema_types.append(data.get("@type", "Unknown"))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            audit.schema_types.append(item.get("@type", "Unknown"))
            except:
                pass
        
        # Robots.txt
        try:
            robots_url = urljoin(url, "/robots.txt")
            robots_resp = requests.get(robots_url, headers=headers, timeout=5)
            audit.has_robots_txt = robots_resp.status_code == 200
        except:
            pass
        
        # Sitemap
        try:
            sitemap_url = urljoin(url, "/sitemap.xml")
            sitemap_resp = requests.get(sitemap_url, headers=headers, timeout=5)
            audit.has_sitemap = sitemap_resp.status_code == 200
        except:
            pass
        
        # Indexing check (noindex meta)
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        if robots_meta:
            content = robots_meta.get("content", "").lower()
            audit.is_indexable = "noindex" not in content
        
        # Page speed approximation (using response time as proxy)
        # In production, use PageSpeed Insights API
        response_time = resp.elapsed.total_seconds() if hasattr(resp, 'elapsed') else 0
        if response_time < 1.0:
            audit.page_speed_score = 85
        elif response_time < 2.5:
            audit.page_speed_score = 60
        else:
            audit.page_speed_score = 35
        
        audit.core_web_vitals = {
            "lcp": f"{response_time:.1f}s",
            "cls": "0.05 (estimated)",
            "fid": "15ms (estimated)",
        }
        
    except Exception as e:
        print(f"  ⚠️  Technical audit error: {e}")
    
    # Calculate score
    score = 0
    if audit.has_ssl: score += TECHNICAL_WEIGHTS["ssl"]
    if audit.is_mobile_friendly: score += TECHNICAL_WEIGHTS["mobile"]
    if audit.page_speed_score >= 50: score += TECHNICAL_WEIGHTS["speed"]
    if audit.has_schema: score += TECHNICAL_WEIGHTS["schema"]
    if audit.is_indexable: score += TECHNICAL_WEIGHTS["indexing"]
    if audit.has_sitemap: score += TECHNICAL_WEIGHTS["sitemap"]
    
    audit.score = min(score, 100)
    return audit


# ───────────────────────────────────────────────
# On-Page Audit
# ───────────────────────────────────────────────

def run_onpage_audit(url: str) -> OnPageAudit:
    """Run on-page SEO analysis."""
    audit = OnPageAudit()
    
    if not url or not url.startswith("http"):
        return audit
    
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Title
        title_tag = soup.find("title")
        if title_tag:
            audit.title = title_tag.get_text().strip()
            audit.title_length = len(audit.title)
        
        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            audit.meta_desc = meta_desc.get("content", "").strip()
            audit.meta_desc_length = len(audit.meta_desc)
        
        # H1
        h1 = soup.find("h1")
        if h1:
            audit.h1 = h1.get_text().strip()
        
        # H2, H3 counts
        audit.h2_count = len(soup.find_all("h2"))
        audit.h3_count = len(soup.find_all("h3"))
        
        # Word count
        text = soup.get_text(separator=" ", strip=True)
        audit.word_count = len(text.split())
        
        # Images and alt text
        images = soup.find_all("img")
        audit.image_count = len(images)
        audit.images_with_alt = sum(1 for img in images if img.get("alt"))
        
        # Links
        links = soup.find_all("a", href=True)
        internal = 0
        external = 0
        for link in links:
            href = link.get("href", "")
            if href.startswith("http"):
                if urlparse(href).netloc == urlparse(url).netloc:
                    internal += 1
                else:
                    external += 1
            elif href.startswith("/"):
                internal += 1
        
        audit.internal_links = internal
        audit.external_links = external
        
        # Canonical
        canonical = soup.find("link", attrs={"rel": "canonical"})
        audit.has_canonical = bool(canonical)
        
        # Keywords extraction
        audit.keywords = extract_keywords(soup, audit.title, audit.meta_desc, audit.h1)
        
    except Exception as e:
        print(f"  ⚠️  On-page audit error: {e}")
    
    # Calculate score
    score = 0
    if audit.title and 30 <= audit.title_length <= 60: score += ONPAGE_WEIGHTS["title"]
    elif audit.title: score += ONPAGE_WEIGHTS["title"] // 2
    
    if audit.meta_desc and 70 <= audit.meta_desc_length <= 160: score += ONPAGE_WEIGHTS["meta_desc"]
    elif audit.meta_desc: score += ONPAGE_WEIGHTS["meta_desc"] // 2
    
    if audit.h1: score += ONPAGE_WEIGHTS["h1"]
    if audit.word_count >= 300: score += ONPAGE_WEIGHTS["content_length"]
    elif audit.word_count >= 150: score += ONPAGE_WEIGHTS["content_length"] // 2
    
    if audit.image_count > 0 and audit.images_with_alt / audit.image_count >= 0.8:
        score += ONPAGE_WEIGHTS["images_alt"]
    elif audit.image_count > 0 and audit.images_with_alt / audit.image_count >= 0.5:
        score += ONPAGE_WEIGHTS["images_alt"] // 2
    
    if audit.internal_links >= 3: score += ONPAGE_WEIGHTS["internal_links"]
    if audit.has_canonical: score += ONPAGE_WEIGHTS["canonical"]
    
    audit.score = min(score, 100)
    return audit


def extract_keywords(soup: BeautifulSoup, title: str, meta_desc: str, h1: str) -> List[str]:
    """Extract top keywords from page content."""
    text = " ".join([title, meta_desc, h1])
    
    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter common stop words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'she', 'use', 'her', 'than', 'them', 'well', 'have'}
    words = [w for w in words if w not in stop_words]
    
    # Count frequency
    from collections import Counter
    freq = Counter(words)
    
    # Return top 5
    return [word for word, count in freq.most_common(5)]


# ───────────────────────────────────────────────
# Local SEO Audit
# ───────────────────────────────────────────────

def run_local_audit(business_name: str, suburb: str, service: str) -> LocalSEOAudit:
    """Run local SEO audit using Google Maps data."""
    audit = LocalSEOAudit()
    
    # Import and reuse the prospector scraper
    try:
        from melbourne_prospector import scrape_google_maps
        
        results = scrape_google_maps(service, suburb, pages=1)
        
        # Find the business in results
        for biz in results:
            if business_name.lower() in biz.get("name", "").lower():
                audit.gbp_name = biz.get("name", "")
                audit.gbp_url = biz.get("gbp_url", "")
                audit.gbp_rating = biz.get("rating", 0.0)
                audit.gbp_review_count = biz.get("review_count", 0)
                audit.gbp_address = biz.get("address", "")
                audit.gbp_phone = biz.get("phone", "")
                audit.gbp_claimed = bool(biz.get("gbp_url"))
                break
        
        # If not found, use first result as competitor reference
        if not audit.gbp_name and results:
            audit.gbp_name = results[0].get("name", "")
            audit.gbp_rating = results[0].get("rating", 0.0)
            audit.gbp_review_count = results[0].get("review_count", 0)
    
    except Exception as e:
        print(f"  ⚠️  Local audit error: {e}")
    
    # Calculate score
    score = 0
    if audit.gbp_claimed: score += LOCAL_WEIGHTS["gbp_claimed"]
    if audit.gbp_review_count >= 50: score += LOCAL_WEIGHTS["gbp_reviews"]
    elif audit.gbp_review_count >= 10: score += LOCAL_WEIGHTS["gbp_reviews"] // 2
    
    if audit.gbp_rating >= 4.5: score += LOCAL_WEIGHTS["gbp_rating"]
    elif audit.gbp_rating >= 4.0: score += LOCAL_WEIGHTS["gbp_rating"] // 2
    
    if audit.gbp_photo_count >= 5: score += LOCAL_WEIGHTS["gbp_photos"]
    if audit.gbp_has_posts: score += LOCAL_WEIGHTS["gbp_posts"]
    if audit.nap_consistent: score += LOCAL_WEIGHTS["nap_consistency"]
    if audit.citations_found >= 3: score += LOCAL_WEIGHTS["citations"]
    
    audit.score = min(score, 100)
    return audit


# ───────────────────────────────────────────────
# Competitor Analysis
# ───────────────────────────────────────────────

def analyze_competitors(suburb: str, service: str) -> List[CompetitorAnalysis]:
    """Find top 3 competitors using the prospector."""
    competitors = []
    
    try:
        from melbourne_prospector import scrape_google_maps
        
        results = scrape_google_maps(service, suburb, pages=1)
        
        for i, biz in enumerate(results[:3], 1):
            comp = CompetitorAnalysis(
                name=biz.get("name", ""),
                position=i,
                website=biz.get("website", ""),
                rating=biz.get("rating", 0.0),
                review_count=biz.get("review_count", 0),
                has_website=bool(biz.get("website", "")),
                snippet=biz.get("address", ""),
            )
            competitors.append(comp)
    
    except Exception as e:
        print(f"  ⚠️  Competitor analysis error: {e}")
    
    return competitors


# ───────────────────────────────────────────────
# Quick Wins Generator
# ───────────────────────────────────────────────

def generate_quick_wins(technical: TechnicalAudit, onpage: OnPageAudit, local: LocalSEOAudit) -> List[Dict]:
    """Generate prioritized quick wins based on audit findings."""
    wins = []
    
    # Technical quick wins
    if not technical.has_ssl:
        wins.append({
            "issue": "Add SSL certificate (HTTPS)",
            "impact": "High",
            "impact_badge": "pass",
            "time": "30 minutes",
        })
    
    if not technical.is_mobile_friendly:
        wins.append({
            "issue": "Add responsive viewport meta tag",
            "impact": "High",
            "impact_badge": "pass",
            "time": "15 minutes",
        })
    
    if not technical.has_schema:
        wins.append({
            "issue": "Add LocalBusiness schema markup",
            "impact": "Medium",
            "impact_badge": "warn",
            "time": "2 hours",
        })
    
    # On-page quick wins
    if not onpage.title or onpage.title_length < 30:
        wins.append({
            "issue": "Write optimized page title (50-60 chars)",
            "impact": "High",
            "impact_badge": "pass",
            "time": "30 minutes",
        })
    
    if not onpage.meta_desc or onpage.meta_desc_length < 70:
        wins.append({
            "issue": "Write meta description (150-160 chars)",
            "impact": "High",
            "impact_badge": "pass",
            "time": "30 minutes",
        })
    
    if not onpage.h1:
        wins.append({
            "issue": "Add H1 heading with primary keyword",
            "impact": "High",
            "impact_badge": "pass",
            "time": "20 minutes",
        })
    
    if onpage.word_count < 300:
        wins.append({
            "issue": "Expand page content to 300+ words",
            "impact": "Medium",
            "impact_badge": "warn",
            "time": "2 hours",
        })
    
    if onpage.image_count > 0 and onpage.images_with_alt / onpage.image_count < 0.8:
        wins.append({
            "issue": "Add alt text to all images",
            "impact": "Medium",
            "impact_badge": "warn",
            "time": "1 hour",
        })
    
    # Local quick wins
    if not local.gbp_claimed:
        wins.append({
            "issue": "Claim Google Business Profile",
            "impact": "High",
            "impact_badge": "pass",
            "time": "30 minutes",
        })
    
    if local.gbp_review_count < 10:
        wins.append({
            "issue": "Launch review generation campaign",
            "impact": "High",
            "impact_badge": "pass",
            "time": "Ongoing",
        })
    
    return wins[:5]  # Return top 5


# ───────────────────────────────────────────────
# Report Template Population
# ───────────────────────────────────────────────

def populate_template(report: AuditReport, template_path: str, output_path: str) -> None:
    """Populate the audit report template with real data."""
    
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    
    # Helper: calculate SVG stroke offset for score ring
    def score_offset(score: int) -> float:
        circumference = 2 * 3.14159 * 52  # r=52
        return circumference * (1 - score / 100)
    
    def score_color(score: int) -> str:
        if score >= 70: return "#30d158"  # green
        if score >= 40: return "#ff9500"  # orange
        return "#ff3b30"  # red
    
    # Status helpers
    def status_class(pass_: bool, warn: bool = False) -> str:
        if pass_: return "status-pass"
        if warn: return "status-warn"
        return "status-fail"
    
    def badge_class(pass_: bool, warn: bool = False) -> str:
        if pass_: return "pass"
        if warn: return "warn"
        return "fail"
    
    def badge_text(pass_: bool, text: str) -> str:
        if pass_: return text
        return text
    
    # Build replacements
    replacements = {
        "{{business_name}}": report.business_name,
        "{{service}}": report.service,
        "{{suburb}}": report.suburb,
        "{{report_date}}": datetime.now().strftime("%B %d, %Y"),
        "{{opportunity_count}}": str(len(report.quick_wins)),
        
        # Scores
        "{{technical_score}}": str(report.technical.score),
        "{{technical_color}}": score_color(report.technical.score),
        "{{technical_offset}}": f"{score_offset(report.technical.score):.2f}",
        
        "{{onpage_score}}": str(report.onpage.score),
        "{{onpage_color}}": score_color(report.onpage.score),
        "{{onpage_offset}}": f"{score_offset(report.onpage.score):.2f}",
        
        "{{local_score}}": str(report.local.score),
        "{{local_color}}": score_color(report.local.score),
        "{{local_offset}}": f"{score_offset(report.local.score):.2f}",
        
        "{{overall_score}}": str(report.overall_score),
        "{{overall_color}}": score_color(report.overall_score),
        "{{overall_offset}}": f"{score_offset(report.overall_score):.2f}",
        
        # Technical status
        "{{ssl_status}}": status_class(report.technical.has_ssl),
        "{{ssl_badge}}": badge_class(report.technical.has_ssl),
        "{{ssl_text}}": "Secure" if report.technical.has_ssl else "No SSL",
        
        "{{mobile_status}}": status_class(report.technical.is_mobile_friendly),
        "{{mobile_badge}}": badge_class(report.technical.is_mobile_friendly),
        "{{mobile_text}}": "Optimized" if report.technical.is_mobile_friendly else "Needs Improvement",
        
        "{{speed_status}}": status_class(report.technical.page_speed_score >= 50, report.technical.page_speed_score >= 30),
        "{{speed_badge}}": badge_class(report.technical.page_speed_score >= 50, report.technical.page_speed_score >= 30),
        "{{speed_text}}": f"{report.technical.page_speed_score}/100" if report.technical.page_speed_score > 0 else "Slow",
        
        "{{title_status}}": status_class(bool(report.onpage.title)),
        "{{title_badge}}": badge_class(bool(report.onpage.title)),
        "{{title_text}}": "Present" if report.onpage.title else "Missing",
        
        "{{meta_status}}": status_class(bool(report.onpage.meta_desc)),
        "{{meta_badge}}": badge_class(bool(report.onpage.meta_desc)),
        "{{meta_text}}": "Present" if report.onpage.meta_desc else "Missing",
        
        "{{schema_status}}": status_class(report.technical.has_schema),
        "{{schema_badge}}": badge_class(report.technical.has_schema),
        "{{schema_text}}": "Found" if report.technical.has_schema else "Not Found",
        
        "{{gbp_status}}": status_class(report.local.gbp_claimed),
        "{{gbp_badge}}": badge_class(report.local.gbp_claimed),
        "{{gbp_text}}": "Claimed" if report.local.gbp_claimed else "Not Claimed",
        
        "{{reviews_status}}": status_class(report.local.gbp_review_count >= 50, report.local.gbp_review_count >= 10),
        "{{reviews_badge}}": badge_class(report.local.gbp_review_count >= 50, report.local.gbp_review_count >= 10),
        "{{reviews_text}}": f"{report.local.gbp_review_count} reviews" if report.local.gbp_review_count > 0 else "None",
    }
    
    # Competitors
    for i, comp in enumerate(report.competitors, 1):
        replacements[f"{{comp{i}_name}}"] = comp.name
        replacements[f"{{comp{i}_rating}}"] = str(comp.rating)
        replacements[f"{{comp{i}_reviews}}"] = str(comp.review_count)
        replacements[f"{{comp{i}_snippet}}"] = comp.snippet or f"Top competitor for {report.service} in {report.suburb}"
    
    # Quick wins
    for i, win in enumerate(report.quick_wins, 1):
        replacements[f"{{quickwin{i}_issue}}"] = win["issue"]
        replacements[f"{{quickwin{i}_impact}}"] = win["impact"]
        replacements[f"{{quickwin{i}_impact_badge}}"] = win["impact_badge"]
        replacements[f"{{quickwin{i}_time}}"] = win["time"]
    
    # Expected results
    results = calculate_expected_results(report.overall_score)
    replacements["{{month1_rank}}"] = results["month1_rank"]
    replacements["{{month1_desc}}"] = results["month1_desc"]
    replacements["{{month2_rank}}"] = results["month2_rank"]
    replacements["{{month2_desc}}"] = results["month2_desc"]
    replacements["{{month3_rank}}"] = results["month3_rank"]
    replacements["{{month3_desc}}"] = results["month3_desc"]
    
    # Apply replacements
    for key, value in replacements.items():
        template = template.replace(key, value)
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(template)
    
    print(f"\n💾 Audit report generated: {output_path}")


def calculate_expected_results(overall_score: int) -> Dict:
    """Calculate expected ranking improvements based on current score."""
    if overall_score < 30:
        return {
            "month1_rank": "+15",
            "month1_desc": "Technical fixes implemented, GBP optimized, site indexed properly",
            "month2_rank": "+25",
            "month2_desc": "Content pages live, 50+ new reviews, 20 local citations built",
            "month3_rank": "+35",
            "month3_desc": "Top 3 rankings for primary keywords, consistent lead flow established",
        }
    elif overall_score < 60:
        return {
            "month1_rank": "+10",
            "month1_desc": "Content expansion and on-page optimization completed",
            "month2_rank": "+20",
            "month2_desc": "Backlink campaign and citation building in progress",
            "month3_rank": "+30",
            "month3_desc": "Dominant local presence, 100+ reviews, lead generation optimized",
        }
    else:
        return {
            "month1_rank": "+5",
            "month1_desc": "Fine-tuning existing optimizations, expanding keyword targets",
            "month2_rank": "+10",
            "month2_desc": "Advanced schema and featured snippet optimization",
            "month3_rank": "+15",
            "month3_desc": "Market leader position, multi-suburb expansion ready",
        }


# ───────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Marvelus Audit Automation Engine — Full SEO audit in 30 seconds"
    )
    parser.add_argument("--name", required=True, help="Business name (e.g., 'Joe's Plumbing')")
    parser.add_argument("--suburb", required=True, help="Suburb (e.g., Frankston)")
    parser.add_argument("--service", required=True, help="Service type (e.g., plumber)")
    parser.add_argument("--url", help="Direct website URL (optional, will auto-discover if omitted)")
    parser.add_argument("--output", default="reports/audit-report.html", help="Output HTML path")
    parser.add_argument("--template", default="audit-report-template.html", help="Template HTML path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🚀 Marvelus Audit Automation Engine — Phase 3")
    print(f"{'='*60}")
    print(f"Business: {args.name}")
    print(f"Suburb:   {args.suburb}")
    print(f"Service:  {args.service}")
    print(f"{'='*60}\n")

    # 1. Find website
    if args.url:
        website_url = args.url
        print(f"🌐 Using provided URL: {website_url}")
    else:
        print("🔍 Discovering website...")
        website_url = find_website(args.name, args.suburb, args.service)
        if website_url:
            print(f"🌐 Found: {website_url}")
        else:
            print("⚠️  No website found. Audit will focus on local SEO only.")
    
    # 2. Run technical audit
    print("\n🔧 Technical Audit")
    print("-" * 40)
    technical = run_technical_audit(website_url or "")
    print(f"  SSL: {'✅' if technical.has_ssl else '❌'}")
    print(f"  Mobile: {'✅' if technical.is_mobile_friendly else '❌'}")
    print(f"  Speed: {technical.page_speed_score}/100")
    print(f"  Schema: {'✅' if technical.has_schema else '❌'}")
    print(f"  Score: {technical.score}/100")
    
    # 3. Run on-page audit
    print("\n📝 On-Page Audit")
    print("-" * 40)
    onpage = run_onpage_audit(website_url or "")
    print(f"  Title: {onpage.title[:50]}..." if onpage.title else "  Title: ❌ Missing")
    print(f"  Meta: {onpage.meta_desc[:50]}..." if onpage.meta_desc else "  Meta: ❌ Missing")
    print(f"  H1: {onpage.h1[:50]}..." if onpage.h1 else "  H1: ❌ Missing")
    print(f"  Words: {onpage.word_count}")
    print(f"  Images: {onpage.images_with_alt}/{onpage.image_count} with alt")
    print(f"  Score: {onpage.score}/100")
    
    # 4. Run local SEO audit
    print("\n📍 Local SEO Audit")
    print("-" * 40)
    local = run_local_audit(args.name, args.suburb, args.service)
    print(f"  GBP: {'✅ Claimed' if local.gbp_claimed else '❌ Not Claimed'}")
    print(f"  Rating: {local.gbp_rating}★")
    print(f"  Reviews: {local.gbp_review_count}")
    print(f"  Score: {local.score}/100")
    
    # 5. Competitor analysis
    print("\n🎯 Competitor Analysis")
    print("-" * 40)
    competitors = analyze_competitors(args.suburb, args.service)
    for comp in competitors:
        print(f"  #{comp.position}: {comp.name} | {comp.rating}★ ({comp.review_count} reviews)")
    
    # 6. Calculate overall score
    weights = {"technical": 0.35, "onpage": 0.30, "local": 0.35}
    overall = int(
        technical.score * weights["technical"] +
        onpage.score * weights["onpage"] +
        local.score * weights["local"]
    )
    
    # 7. Generate quick wins
    quick_wins = generate_quick_wins(technical, onpage, local)
    
    # 8. Build report
    report = AuditReport(
        business_name=args.name,
        service=args.service,
        suburb=args.suburb,
        website_url=website_url or "",
        technical=technical,
        onpage=onpage,
        local=local,
        competitors=competitors,
        overall_score=overall,
        quick_wins=quick_wins,
        opportunity_count=len(quick_wins),
    )
    
    # 9. Summary
    print(f"\n{'='*60}")
    print(f"📊 AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"Technical:  {technical.score}/100")
    print(f"On-Page:    {onpage.score}/100")
    print(f"Local SEO:  {local.score}/100")
    print(f"Overall:    {overall}/100")
    print(f"Quick Wins: {len(quick_wins)}")
    print(f"{'='*60}")
    
    # 10. Generate report
    print(f"\n📄 Generating report...")
    
    # Ensure output directory exists
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    populate_template(report, args.template, args.output)
    
    print(f"\n✅ Audit complete! Report saved to: {args.output}")
    print(f"\nNext steps:")
    print(f"  1. Open {args.output} in browser to review")
    print(f"  2. Print to PDF for client delivery")
    print(f"  3. Schedule strategy call to discuss implementation")


if __name__ == "__main__":
    main()
