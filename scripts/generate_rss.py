#!/usr/bin/env python3
"""
Generate RSS 2.0 feed from papers.json.
"""

import json
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist"
PAPERS_JSON = DATA_DIR / "papers.json"
RSS_FILE = DIST_DIR / "feed.xml"

SITE_URL = "https://yourusername.github.io/Awesome-Gaussian-Splatting"
FEED_TITLE = "Awesome Gaussian Splatting Latest Papers"
FEED_DESCRIPTION = "Daily updated feed of the latest Gaussian Splatting papers from arXiv."
MAX_ITEMS = 50


def iso_to_rfc822(iso_str: str) -> str:
    """Convert ISO 8601 datetime string to RFC 822 format for RSS."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return format_datetime(dt)
    except (ValueError, AttributeError):
        return ""


def generate_rss():
    print("=" * 60)
    print("Generating RSS feed")
    print("=" * 60)

    with open(PAPERS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = data.get("papers", [])[:MAX_ITEMS]
    print(f"  Including {len(papers)} papers in RSS feed")

    # Build RSS XML
    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = FEED_TITLE
    SubElement(channel, "link").text = SITE_URL
    SubElement(channel, "description").text = FEED_DESCRIPTION
    SubElement(channel, "language").text = "en-us"

    last_updated = data.get("last_updated", "")
    if last_updated:
        SubElement(channel, "lastBuildDate").text = iso_to_rfc822(last_updated)

    # Self-referencing atom link
    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{SITE_URL}/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for paper in papers:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = paper.get("title", "")
        SubElement(item, "link").text = paper.get("abs_url", "")
        SubElement(item, "guid").text = paper.get("abs_url", "")

        # Truncate abstract to 500 chars for description
        abstract = paper.get("abstract", "")
        if len(abstract) > 500:
            abstract = abstract[:497] + "..."
        SubElement(item, "description").text = abstract

        pub_date = paper.get("published", "")
        if pub_date:
            SubElement(item, "pubDate").text = iso_to_rfc822(pub_date)

        # Add categories/tags
        for tag in paper.get("tags", []):
            SubElement(item, "category").text = tag

        # Authors
        authors = paper.get("authors", [])
        if authors:
            SubElement(item, "author").text = ", ".join(authors[:5])
            if len(authors) > 5:
                SubElement(item, "author").text = ", ".join(authors[:5]) + " et al."

    # Write XML
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_body = tostring(rss, encoding="unicode")
    RSS_FILE.write_text(xml_declaration + xml_body, encoding="utf-8")
    print(f"  Generated {RSS_FILE}")
    print("\nRSS generation complete!")


if __name__ == "__main__":
    generate_rss()
