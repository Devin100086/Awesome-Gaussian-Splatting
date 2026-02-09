# ? Awesome Gaussian Splatting Papers

[![Fetch & Deploy](https://github.com/AuroraAegis/Awesome-Gaussian-Splatting/actions/workflows/fetch-and-deploy.yml/badge.svg)](https://github.com/AuroraAegis/Awesome-Gaussian-Splatting/actions/workflows/fetch-and-deploy.yml)

> **Auto-updated daily** ¡ª A curated, searchable collection of the latest Gaussian Splatting papers from [arXiv](https://arxiv.org), deployed as a static website via GitHub Pages.

? **Live Site**: [https://AuroraAegis.github.io/Awesome-Gaussian-Splatting](https://AuroraAegis.github.io/Awesome-Gaussian-Splatting)

---

## Features

- ? **Daily arXiv Sync** ¡ª Automatically fetches new Gaussian Splatting papers every day via GitHub Actions
- ? **Full-text Search** ¡ª Search by title, author, or abstract keywords
- ?? **Tag Filtering** ¡ª Papers are auto-tagged (Dynamic, SLAM, Avatar, Compression, Medical, etc.)
- ? **Time Filtering** ¡ª Filter papers by year and month
- ? **Sorting** ¡ª Sort by date or title (ascending / descending)
- ? **Paper Details** ¡ª Click any paper card to view full abstract and metadata
- ? **Dark Mode** ¡ª Automatic system preference detection + manual toggle
- ? **RSS Feed** ¡ª Subscribe to `feed.xml` for updates in your RSS reader
- ? **Responsive** ¡ª Works on desktop, tablet, and mobile

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | [arXiv API](https://info.arxiv.org/help/api/index.html) (Atom XML) |
| Scraper | Python (`requests` + `feedparser`) |
| Build | Python (`jinja2` template injection) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| CI/CD | GitHub Actions (daily cron) |
| Hosting | GitHub Pages |
| Feed | RSS 2.0 XML |

## Project Structure

```
©À©¤©¤ .github/workflows/
©¦   ©¸©¤©¤ fetch-and-deploy.yml   # Daily cron + manual trigger workflow
©À©¤©¤ scripts/
©¦   ©À©¤©¤ fetch_papers.py        # arXiv API scraper (incremental updates)
©¦   ©À©¤©¤ build_site.py          # Static site generator
©¦   ©À©¤©¤ generate_rss.py        # RSS feed generator
©¦   ©¸©¤©¤ requirements.txt       # Python dependencies
©À©¤©¤ data/
©¦   ©¸©¤©¤ papers.json            # All papers data (auto-updated)
©À©¤©¤ src/
©¦   ©À©¤©¤ templates/
©¦   ©¦   ©¸©¤©¤ index.html         # HTML template
©¦   ©À©¤©¤ css/
©¦   ©¦   ©¸©¤©¤ style.css          # Styles (light + dark theme)
©¦   ©¸©¤©¤ js/
©¦       ©¸©¤©¤ app.js             # Frontend logic
©À©¤©¤ dist/                      # Build output (deployed to gh-pages)
©À©¤©¤ README.md
©¸©¤©¤ LICENSE
```

## Local Development

### Prerequisites

- Python 3.10+

### Setup

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Fetch papers from arXiv (takes a few minutes)
python scripts/fetch_papers.py

# Build the static site
python scripts/build_site.py

# Generate RSS feed
python scripts/generate_rss.py

# Preview locally ¡ª open dist/index.html in your browser
```

### Quick Test (without fetching)

If you just want to test the frontend with sample data, you can directly open `dist/index.html` after running `build_site.py` with the existing `data/papers.json`.

## Deployment

This project is designed to run entirely on GitHub:

1. **Fork** this repository
2. Go to **Settings ¡ú Pages** and set source to `gh-pages` branch
3. Go to **Settings ¡ú Actions ¡ú General** and enable workflow permissions (Read & Write)
4. **Run the workflow** manually from the Actions tab, or wait for the daily cron
5. Your site will be live at `https://<username>.github.io/Awesome-Gaussian-Splatting/`

## Auto-Tagging

Papers are automatically tagged based on keyword matching in titles and abstracts. Current tag categories:

`Dynamic` ¡¤ `SLAM` ¡¤ `Avatar` ¡¤ `Autonomous Driving` ¡¤ `Medical` ¡¤ `Compression` ¡¤ `Mesh` ¡¤ `Rendering` ¡¤ `Editing` ¡¤ `Generation` ¡¤ `Segmentation` ¡¤ `Physics` ¡¤ `Sparse View` ¡¤ `Language` ¡¤ `Robotics`

Tag rules can be customized in `scripts/fetch_papers.py` ¡ú `TAG_RULES`.

## Acknowledgments

- Thank you to [arXiv](https://arxiv.org) for use of its open access interoperability
- Inspired by [MrNeRF/awesome-3D-gaussian-splatting](https://github.com/MrNeRF/awesome-3D-gaussian-splatting)

## License

[MIT](LICENSE) ? AuroraAegis