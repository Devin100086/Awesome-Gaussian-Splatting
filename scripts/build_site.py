#!/usr/bin/env python3
"""
Build static site from papers.json + HTML template.
Outputs to dist/ directory.
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
PAPERS_JSON = DATA_DIR / "papers.json"
TEMPLATE_FILE = SRC_DIR / "templates" / "index.html"


def read_text_with_fallback(path: Path) -> str:
    """Read text file with UTF-8 first, then fallback encodings."""
    for enc in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    # Last resort: replace invalid characters
    return path.read_text(encoding="utf-8", errors="replace")


def load_papers() -> dict:
    """Load papers data from JSON file with encoding fallback."""
    for enc in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            with open(PAPERS_JSON, "r", encoding=enc) as f:
                return json.load(f)
        except UnicodeDecodeError:
            continue
    with open(PAPERS_JSON, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def build():
    print("=" * 60)
    print("Building static site")
    print("=" * 60)

    # Clean and create dist directory
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    # Load data
    data = load_papers()
    papers_json_str = json.dumps(data, ensure_ascii=False)
    print(f"  Loaded {data['total_count']} papers")

    # Read HTML template
    template = read_text_with_fallback(TEMPLATE_FILE)

    # Inject papers data into template
    html = template.replace("/* __PAPERS_DATA_PLACEHOLDER__ */", f"const PAPERS_DATA = {papers_json_str};")

    # Write index.html
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")
    print("  Generated dist/index.html")

    # Copy static assets
    css_src = SRC_DIR / "css"
    js_src = SRC_DIR / "js"

    if css_src.exists():
        shutil.copytree(css_src, DIST_DIR / "css")
        print("  Copied css/")

    if js_src.exists():
        shutil.copytree(js_src, DIST_DIR / "js")
        print("  Copied js/")

    # Also copy papers.json to dist for potential lazy-loading
    shutil.copy2(PAPERS_JSON, DIST_DIR / "papers.json")
    print("  Copied papers.json")

    print("\nBuild complete! Output in dist/")


if __name__ == "__main__":
    build()
