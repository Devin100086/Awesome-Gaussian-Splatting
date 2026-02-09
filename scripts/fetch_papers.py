#!/usr/bin/env python3
"""
Fetch latest Gaussian Splatting papers from arXiv API.
Supports incremental updates - only new papers are appended.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ARXIV_API_URL = "http://export.arxiv.org/api/query"
SEARCH_QUERY = 'all:"gaussian splatting" OR all:"3d gaussian" OR all:"3dgs" OR all:"gaussian splat"'
MAX_RESULTS_PER_PAGE = 100
MAX_TOTAL_RESULTS = 5000          # safety cap
REQUEST_DELAY = 3                 # seconds between API calls
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PAPERS_JSON = DATA_DIR / "papers.json"

# ---------------------------------------------------------------------------
# Tag rules: keyword patterns (case-insensitive) → tag name
# ---------------------------------------------------------------------------
TAG_RULES: dict[str, list[str]] = {
    "Dynamic": [
        r"dynamic", r"deformable", r"temporal", r"4d[\s\-]",
        r"time[\s\-]varying", r"motion"
    ],
    "SLAM": [
        r"\bslam\b", r"simultaneous localization", r"visual odometry",
        r"mapping and localization"
    ],
    "Avatar": [
        r"avatar", r"human body", r"human reconstruction",
        r"animatable", r"body model", r"face reconstruction",
        r"head avatar", r"hand avatar", r"drivable"
    ],
    "Autonomous Driving": [
        r"autonomous driving", r"self[\s\-]driving", r"street[\s\-]view",
        r"urban scene", r"driving scene", r"lidar"
    ],
    "Medical": [
        r"medical", r"surgical", r"endoscop", r"colonoscop",
        r"ct[\s\-]", r"mri[\s\-]", r"radiology", r"anatomy"
    ],
    "Compression": [
        r"compress", r"compact", r"pruning", r"quantiz",
        r"lightweight", r"efficient representation"
    ],
    "Mesh": [
        r"\bmesh\b", r"surface reconstruction", r"marching cubes",
        r"sdf[\s\-]", r"signed distance"
    ],
    "Rendering": [
        r"real[\s\-]time rendering", r"novel view", r"view synthesis",
        r"relighting", r"anti[\s\-]alias", r"ray tracing"
    ],
    "Editing": [
        r"editing", r"manipulation", r"styliz", r"text[\s\-]driven",
        r"inpainting", r"scene editing"
    ],
    "Generation": [
        r"generat", r"diffusion", r"text[\s\-]to[\s\-]3d",
        r"image[\s\-]to[\s\-]3d", r"dreamfusion", r"score distillation"
    ],
    "Segmentation": [
        r"segment", r"semantic", r"panoptic", r"instance[\s\-]",
        r"object[\s\-]detection"
    ],
    "Physics": [
        r"physic", r"simulat", r"fluid", r"cloth", r"elastic",
        r"deformation"
    ],
    "Sparse View": [
        r"sparse[\s\-]view", r"few[\s\-]shot", r"single[\s\-]image",
        r"one[\s\-]shot", r"limited view"
    ],
    "Language": [
        r"language", r"\bllm\b", r"\bclip\b", r"open[\s\-]vocabulary",
        r"text[\s\-]guided", r"natural language"
    ],
    "Robotics": [
        r"robot", r"grasp", r"manipulat", r"navigation",
        r"planning"
    ],
}


def assign_tags(title: str, abstract: str) -> list[str]:
    """Assign tags based on keyword matching in title + abstract."""
    text = f"{title} {abstract}".lower()
    tags = []
    for tag, patterns in TAG_RULES.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                tags.append(tag)
                break
    return sorted(tags)


def fetch_arxiv_papers() -> list[dict]:
    """Fetch papers from arXiv API with pagination."""
    all_papers: list[dict] = []
    start = 0

    while start < MAX_TOTAL_RESULTS:
        params = {
            "search_query": SEARCH_QUERY,
            "start": start,
            "max_results": MAX_RESULTS_PER_PAGE,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        print(f"  Fetching results {start}–{start + MAX_RESULTS_PER_PAGE} ...")

        try:
            # Try direct connection first (bypass proxy)
            resp = requests.get(ARXIV_API_URL, params=params, timeout=30,
                                proxies={"http": None, "https": None})
        except requests.exceptions.ConnectionError:
            # Fallback: use system proxy
            resp = requests.get(ARXIV_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        if not feed.entries:
            print("  No more entries, stopping.")
            break

        for entry in feed.entries:
            arxiv_id = entry.id.split("/abs/")[-1]
            # Remove version suffix for dedup (e.g., "2401.12345v2" → "2401.12345")
            arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)

            pdf_url = ""
            for link in entry.get("links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link.href
                    break

            categories = [t.term for t in entry.get("tags", [])]
            authors = [a.name for a in entry.get("authors", [])]

            paper = {
                "id": arxiv_id_base,
                "title": re.sub(r"\s+", " ", entry.title).strip(),
                "authors": authors,
                "abstract": re.sub(r"\s+", " ", entry.summary).strip(),
                "published": entry.published,
                "updated": entry.updated,
                "categories": categories,
                "pdf_url": pdf_url,
                "abs_url": f"https://arxiv.org/abs/{arxiv_id_base}",
                "tags": [],  # will be filled later
            }
            all_papers.append(paper)

        # If we got fewer entries than requested, we've reached the end
        if len(feed.entries) < MAX_RESULTS_PER_PAGE:
            print(f"  Got {len(feed.entries)} entries (< {MAX_RESULTS_PER_PAGE}), done.")
            break

        start += MAX_RESULTS_PER_PAGE
        print(f"  Waiting {REQUEST_DELAY}s before next request...")
        time.sleep(REQUEST_DELAY)

    return all_papers


def load_existing_papers() -> dict:
    """Load existing papers.json data."""
    if PAPERS_JSON.exists():
        with open(PAPERS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": "", "total_count": 0, "papers": []}


def merge_papers(existing: list[dict], new_papers: list[dict]) -> list[dict]:
    """Merge new papers into existing list, deduplicating by ID.
    Preserves manually-edited tags in existing entries.
    """
    existing_map = {p["id"]: p for p in existing}
    added = 0

    for paper in new_papers:
        pid = paper["id"]
        if pid not in existing_map:
            paper["tags"] = assign_tags(paper["title"], paper["abstract"])
            existing_map[pid] = paper
            added += 1
        else:
            # Update metadata but preserve manually-edited tags
            old_tags = existing_map[pid].get("tags", [])
            existing_map[pid].update(paper)
            existing_map[pid]["tags"] = old_tags if old_tags else assign_tags(
                paper["title"], paper["abstract"]
            )

    print(f"  Added {added} new papers, {len(existing_map)} total.")

    # Sort by published date descending
    merged = sorted(
        existing_map.values(),
        key=lambda p: p.get("published", ""),
        reverse=True,
    )
    return merged


def save_papers(papers: list[dict]) -> None:
    """Save papers list to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_count": len(papers),
        "papers": papers,
    }
    with open(PAPERS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(papers)} papers to {PAPERS_JSON}")


def main():
    print("=" * 60)
    print("Fetching Gaussian Splatting papers from arXiv")
    print("=" * 60)

    existing_data = load_existing_papers()
    existing_papers = existing_data.get("papers", [])
    print(f"Existing papers: {len(existing_papers)}")

    print("\nFetching from arXiv API...")
    new_papers = fetch_arxiv_papers()
    print(f"Fetched {len(new_papers)} papers from arXiv.\n")

    print("Merging papers...")
    merged = merge_papers(existing_papers, new_papers)

    print("Saving...")
    save_papers(merged)

    print("\nDone!")


if __name__ == "__main__":
    main()
