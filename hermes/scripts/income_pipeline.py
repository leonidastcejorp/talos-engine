#!/usr/bin/env python3
"""
Talos Engine - Income Pipeline Scraper

Scrapes income opportunities from:
- Reddit (r/forhire, r/slavelabour, r/Jobs4Bitcoins)
- Freelancer.com (public listings)

Outputs formatted opportunities for review.

Usage:
    python scripts/income_pipeline.py
    python scripts/income_pipeline.py --sources reddit freelancer
    python scripts/income_pipeline.py --min-budget 50
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

# ─── Data Models ────────────────────────────────────────────────────────────


@dataclass
class Opportunity:
    """An income opportunity."""
    title: str
    url: str
    source: str
    budget: Optional[str] = None
    description: str = ""
    posted: str = ""
    score: int = 0  # Reddit upvotes or relevance score

    @property
    def display_line(self) -> str:
        budget_str = f" [{self.budget}]" if self.budget else ""
        return f"• {self.source.upper()}: {self.title}{budget_str}\n  {self.url}"


# ─── Reddit Scraper ─────────────────────────────────────────────────────────


REDDIT_SUBREDDITS = [
    "forhire",
    "slavelabour",
    "Jobs4Bitcoins",
    "freelance_forhire",
    "jobbit",
]

REDDIT_SEARCH_TERMS = [
    "python developer",
    "web scraping",
    "automation",
    "bot development",
    "data entry",
    "virtual assistant",
    "script",
    "API integration",
]


def fetch_reddit_opportunities(subreddits: List[str] = None) -> List[Opportunity]:
    """Scrape Reddit for income opportunities using public JSON API."""
    opportunities = []
    subs = subreddits or REDDIT_SUBREDDITS

    import urllib.request

    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Talos-Engine/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            for post in data.get("data", {}).get("children", []):
                post_data = post["data"]
                title = post_data.get("title", "")
                post_url = f"https://reddit.com{post_data.get('permalink', '')}"
                description = post_data.get("selftext", "")[:300]
                score = post_data.get("score", 0)

                # Skip stickied posts
                if post_data.get("stickied"):
                    continue

                # Look for budget patterns
                budget = None
                budget_match = re.search(
                    r'\$(\d+[,\d]*(?:\.\d{2})?)', title + description
                )
                if budget_match:
                    budget = f"${budget_match.group(1)}"

                # Also check for "hiring" tag
                if post_data.get("link_flair_text") == "Hiring":
                    budget = budget or "[HIRING]"

                opportunities.append(Opportunity(
                    title=title[:150],
                    url=post_url,
                    source=f"reddit/r/{sub}",
                    budget=budget,
                    description=description,
                    score=score,
                ))

        except Exception as e:
            log_error(
                message=f"Reddit scrape failed for r/{sub}: {e}",
                level=ErrorLevel.WARNING,
                source="income_pipeline",
            )

    # Sort by score (relevance)
    opportunities.sort(key=lambda o: o.score, reverse=True)
    return opportunities[:30]


# ─── Freelancer Scraper ─────────────────────────────────────────────────────


def fetch_freelancer_opportunities() -> List[Opportunity]:
    """Scrape Freelancer.com for relevant projects."""
    opportunities = []
    import urllib.request

    keywords = [
        "python", "automation", "web scraping", "bot",
        "script", "data extraction",
    ]

    for keyword in keywords:
        try:
            url = (
                f"https://www.freelancer.com/api/projects/0.1/projects/active/"
                f"?query={quote(keyword)}&limit=10&compact=true"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Talos-Engine/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            for project in data.get("result", {}).get("projects", []):
                budget = None
                if project.get("budget", {}).get("minimum"):
                    min_b = project["budget"]["minimum"]
                    max_b = project["budget"].get("maximum", min_b)
                    currency = project.get("currency", {}).get("code", "USD")
                    budget = f"{currency} {min_b}-{max_b}"

                opportunities.append(Opportunity(
                    title=project.get("title", "")[:150],
                    url=f"https://www.freelancer.com/projects/"
                        f"{project.get('seo_url', '')}",
                    source="freelancer",
                    budget=budget,
                    description=project.get("description", "")[:300],
                    score=project.get("bid_count", 0),
                ))

        except Exception as e:
            log_error(
                message=f"Freelancer scrape failed for '{keyword}': {e}",
                level=ErrorLevel.WARNING,
                source="income_pipeline",
            )

    opportunities.sort(key=lambda o: o.score, reverse=True)
    return opportunities[:20]


# ─── Main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Income Pipeline Scraper"
    )
    parser.add_argument(
        "--sources", nargs="+", default=["reddit", "freelancer"],
        choices=["reddit", "freelancer"],
        help="Sources to scrape (default: both)",
    )
    parser.add_argument(
        "--min-budget", type=int, default=0,
        help="Minimum budget/amount filter (e.g., 50 for $50+)",
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="Save results to JSON file",
    )
    args = parser.parse_args()

    all_opportunities = []

    if "reddit" in args.sources:
        print("🔍 Scanning Reddit...")
        reddit_opps = fetch_reddit_opportunities()
        all_opportunities.extend(reddit_opps)
        print(f"   Found {len(reddit_opps)} opportunities")

    if "freelancer" in args.sources:
        print("🔍 Scanning Freelancer...")
        freelance_opps = fetch_freelancer_opportunities()
        all_opportunities.extend(freelance_opps)
        print(f"   Found {len(freelance_opps)} opportunities")

    # Filter by budget
    if args.min_budget > 0:
        all_opportunities = [
            o for o in all_opportunities
            if o.budget and _budget_value(o.budget) >= args.min_budget
        ]
        print(f"   After budget filter (≥${args.min_budget}): {len(all_opportunities)}")

    # Sort by score
    all_opportunities.sort(key=lambda o: o.score, reverse=True)

    # Display
    print(f"\n{'='*60}")
    print(f"  💰 Income Pipeline — {len(all_opportunities)} Opportunities")
    print(f"{'='*60}\n")

    if not all_opportunities:
        print("  No opportunities found matching your criteria.")
        return

    for i, opp in enumerate(all_opportunities[:30], 1):
        print(f"{i:2d}. {opp.display_line}")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "title": o.title,
                "url": o.url,
                "source": o.source,
                "budget": o.budget,
                "description": o.description,
                "score": o.score,
            }
            for o in all_opportunities
        ]
        output_path.write_text(json.dumps(data, indent=2))
        print(f"\n📁 Saved to {args.output}")


def _budget_value(budget_str: str) -> float:
    """Extract numeric value from budget string."""
    match = re.search(r'[\d,]+(?:\.\d{2})?', budget_str.replace(",", ""))
    if match:
        return float(match.group())
    return 0


if __name__ == "__main__":
    main()
