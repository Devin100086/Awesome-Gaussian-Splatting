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
from urllib.parse import urljoin

import feedparser
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:  # Optional dependency for method figure extraction
    BeautifulSoup = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ARXIV_API_URL = "http://export.arxiv.org/api/query"
# Use ti: (title) and abs: (abstract) for precise matching instead of all:
# Avoid overly generic terms like "3d gaussian" which matches any 3D Gaussian distribution paper
SEARCH_QUERY = (
    'ti:"gaussian splatting" OR abs:"gaussian splatting" '
    'OR ti:"3d gaussian splatting" OR abs:"3d gaussian splatting" '
    'OR ti:"3DGS" OR abs:"3DGS" '
    'OR ti:"gaussian splat" OR abs:"gaussian splat" '
    'OR ti:"3d gaussians" OR abs:"3d gaussians" '
    'OR ti:"gaussian surfel" OR abs:"gaussian surfel" '
    'OR ti:"splatting" AND abs:"gaussian"'
)
MAX_RESULTS_PER_PAGE = 100
MAX_TOTAL_RESULTS = 5000          # safety cap
REQUEST_DELAY = 3                 # seconds between API calls
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PAPERS_JSON = DATA_DIR / "papers.json"
MIN_PUBLISHED_YEAR = 2024         # Only include papers after 2023

# ---------------------------------------------------------------------------
# Method figure extraction (arXiv HTML)
# ---------------------------------------------------------------------------
FETCH_METHOD_FIGURES = True
FIGURE_BACKFILL = False           # True to fill missing figures for all papers
FIGURE_REQUEST_DELAY = 1          # seconds between figure requests
MAX_FIGURE_FETCH = 50             # safety cap per run
METHOD_FIGURE_KEYWORDS = [
    "method", "architecture", "pipeline", "framework", "overview",
    "system", "approach", "model", "network",
]

# ---------------------------------------------------------------------------
# Relevance filter: papers MUST contain at least one of these in title/abstract
# ---------------------------------------------------------------------------
RELEVANCE_PATTERNS = [
    r"gaussian\s+splat",          # gaussian splatting / gaussian splat
    r"3d\s*gaussian",             # 3D Gaussian(s)
    r"\b3dgs\b",                  # 3DGS acronym
    r"gaussian\s+surfel",         # gaussian surfel
    r"splat\w*\s+gaussian",       # "splatting gaussian" variants
    r"\bneural\s+gaussian",       # neural gaussian
    r"\bgaussian\s+render",       # gaussian rendering
    r"\bgaussian\s+rasteriz",     # gaussian rasterization
    r"point[\s\-]based\s+.*gaussian",  # point-based ... gaussian
]

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

HTML_LINK_RE = re.compile(r'href="(/html/[^"]+)"[^>]*>\s*HTML', re.IGNORECASE)
YEAR_RE = re.compile(r"^(\d{4})-")


def http_get(url: str, params: dict | None = None) -> requests.Response:
    """HTTP GET with proxy fallback (arXiv may reject some proxies)."""
    try:
        return requests.get(url, params=params, timeout=30,
                            proxies={"http": None, "https": None})
    except requests.exceptions.ConnectionError:
        return requests.get(url, params=params, timeout=30)


def get_published_year(published: str | None) -> int | None:
    """Extract year from arXiv published string."""
    if not published:
        return None
    match = YEAR_RE.match(published)
    if not match:
        return None
    return int(match.group(1))


def is_after_min_year(published: str | None) -> bool:
    year = get_published_year(published)
    return year is not None and year >= MIN_PUBLISHED_YEAR


def find_arxiv_html_url(abs_url: str) -> str | None:
    """Find arXiv HTML URL from the abstract page."""
    resp = http_get(abs_url)
    if resp.status_code != 200:
        return None
    match = HTML_LINK_RE.search(resp.text)
    if not match:
        return None
    return urljoin(abs_url, match.group(1))


def score_figure_caption(text: str, index: int) -> float:
    """Heuristic scoring for likely method figures."""
    text_l = text.lower()
    score = 0.0
    if re.search(r"\bfigure\s*1\b", text_l):
        score += 3.0
    for kw in METHOD_FIGURE_KEYWORDS:
        if kw in text_l:
            score += 1.0
    # Prefer earlier figures slightly
    score -= index * 0.01
    return score


def extract_method_figure(html_url: str) -> tuple[str | None, str | None]:
    """Extract a likely method figure image URL + caption from arXiv HTML."""
    if BeautifulSoup is None:
        return None, None
    resp = http_get(html_url)
    if resp.status_code != 200:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    best_url = None
    best_caption = None
    best_score = -1e9

    figures = soup.find_all("figure")
    for idx, fig in enumerate(figures):
        img = fig.find("img")
        if not img or not img.get("src"):
            continue
        caption_el = fig.find("figcaption")
        if not caption_el:
            caption_el = fig.find(class_=re.compile("caption", re.IGNORECASE))
        caption = " ".join(caption_el.stripped_strings) if caption_el else ""
        alt = img.get("alt", "")
        score = score_figure_caption(f"{caption} {alt}", idx)
        if score > best_score:
            best_score = score
            best_url = urljoin(html_url, img["src"])
            best_caption = caption.strip()

    if best_url:
        return best_url, best_caption or None
    return None, None


def is_relevant(title: str, abstract: str) -> bool:
    """Check if a paper is actually about Gaussian Splatting.
    arXiv API returns loose matches; this filters out irrelevant results.
    """
    text = f"{title} {abstract}".lower()
    for pat in RELEVANCE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


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


def enrich_method_figure(paper: dict) -> bool:
    """Fetch and attach a likely method figure URL to a paper."""
    if not FETCH_METHOD_FIGURES:
        return False
    if not paper.get("abs_url"):
        return False
    if paper.get("method_fig_url"):
        return False

    html_url = find_arxiv_html_url(paper["abs_url"])
    if not html_url:
        return False

    fig_url, caption = extract_method_figure(html_url)
    if not fig_url:
        return False

    paper["method_fig_url"] = fig_url
    paper["method_fig_source"] = html_url
    if caption:
        paper["method_fig_caption"] = caption
    return True


def enrich_method_figures(papers: list[dict], target_ids: set[str]) -> None:
    """Enrich a subset of papers with method figures."""
    if not FETCH_METHOD_FIGURES:
        return
    if BeautifulSoup is None:
        print("  bs4 not installed; skipping method figure extraction.")
        return

    candidates = [p for p in papers if p.get("id") in target_ids and not p.get("method_fig_url")]
    if FIGURE_BACKFILL:
        candidates = [p for p in papers if not p.get("method_fig_url")]

    if MAX_FIGURE_FETCH:
        candidates = candidates[:MAX_FIGURE_FETCH]

    if not candidates:
        return

    print(f"Fetching method figures for {len(candidates)} papers...")
    for idx, paper in enumerate(candidates, 1):
        pid = paper.get("id", "")
        print(f"  [{idx}/{len(candidates)}] {pid}")
        try:
            found = enrich_method_figure(paper)
            if found:
                print("    Found method figure.")
            else:
                print("    No method figure found.")
        except requests.RequestException as exc:
            print(f"    Failed to fetch method figure: {exc}")

        if idx < len(candidates):
            time.sleep(FIGURE_REQUEST_DELAY)


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

        resp = http_get(ARXIV_API_URL, params=params)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        if not feed.entries:
            print("  No more entries, stopping.")
            break

        skipped = 0
        skipped_old = 0
        for entry in feed.entries:
            arxiv_id = entry.id.split("/abs/")[-1]
            # Remove version suffix for dedup (e.g., "2401.12345v2" → "2401.12345")
            arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)

            title = re.sub(r"\s+", " ", entry.title).strip()
            abstract = re.sub(r"\s+", " ", entry.summary).strip()

            # Year filter: only keep papers after 2023
            if not is_after_min_year(entry.published):
                skipped_old += 1
                continue

            # Relevance filter: skip papers that don't actually mention GS
            if not is_relevant(title, abstract):
                skipped += 1
                continue

            pdf_url = ""
            for link in entry.get("links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link.href
                    break

            categories = [t.term for t in entry.get("tags", [])]
            authors = [a.name for a in entry.get("authors", [])]

            paper = {
                "id": arxiv_id_base,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "published": entry.published,
                "updated": entry.updated,
                "categories": categories,
                "pdf_url": pdf_url,
                "abs_url": f"https://arxiv.org/abs/{arxiv_id_base}",
                "tags": [],  # will be filled later
            }
            all_papers.append(paper)

        if skipped:
            print(f"  Filtered out {skipped} irrelevant papers in this batch.")
        if skipped_old:
            print(f"  Skipped {skipped_old} papers older than {MIN_PUBLISHED_YEAR}.")

        last_year = get_published_year(feed.entries[-1].published)
        if last_year is not None and last_year < MIN_PUBLISHED_YEAR:
            print("  Reached papers older than cutoff year, stopping.")
            break

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


def merge_papers(existing: list[dict], new_papers: list[dict]) -> tuple[list[dict], list[str]]:
    """Merge new papers into existing list, deduplicating by ID.
    Preserves manually-edited tags in existing entries.
    """
    existing_map = {p["id"]: p for p in existing}
    added_ids: list[str] = []

    for paper in new_papers:
        pid = paper["id"]
        if pid not in existing_map:
            paper["tags"] = assign_tags(paper["title"], paper["abstract"])
            existing_map[pid] = paper
            added_ids.append(pid)
        else:
            # Update metadata but preserve manually-edited tags
            old_tags = existing_map[pid].get("tags", [])
            existing_map[pid].update(paper)
            existing_map[pid]["tags"] = old_tags if old_tags else assign_tags(
                paper["title"], paper["abstract"]
            )

    print(f"  Added {len(added_ids)} new papers, {len(existing_map)} total.")

    filtered = [p for p in existing_map.values() if is_after_min_year(p.get("published"))]
    removed = len(existing_map) - len(filtered)
    if removed:
        print(f"  Removed {removed} papers older than {MIN_PUBLISHED_YEAR}.")

    # Sort by published date descending
    merged = sorted(
        filtered,
        key=lambda p: p.get("published", ""),
        reverse=True,
    )
    return merged, added_ids


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
    merged, added_ids = merge_papers(existing_papers, new_papers)

    if FETCH_METHOD_FIGURES:
        enrich_method_figures(merged, set(added_ids))

    print("Saving...")
    save_papers(merged)

    print("\nDone!")


if __name__ == "__main__":
    main()
