/**
 * Awesome Gaussian Splatting ¡ª Frontend Application
 * Search, filter, sort, paginate, modal, dark mode
 */

(function () {
  "use strict";

  // ©¤©¤ State ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  let allPapers = [];
  let filteredPapers = [];
  let displayedCount = 0;
  const PAGE_SIZE = 50;
  let latestPaperId = null;

  let activeSearchQuery = "";
  let activeYear = "";
  let activeMonth = "";
  let activeTags = new Set();
  let activeSort = "date-desc";

  // ©¤©¤ DOM Elements ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const searchInput     = $("#searchInput");
  const yearFilter      = $("#yearFilter");
  const monthFilter     = $("#monthFilter");
  const sortSelect      = $("#sortSelect");
  const tagFilterEl     = $("#tagFilter");
  const clearTagsBtn    = $("#clearTags");
  const paperList       = $("#paperList");
  const loadMoreWrap    = $("#loadMore");
  const loadMoreBtn     = $("#loadMoreBtn");
  const noResults       = $("#noResults");
  const totalCountEl    = $("#totalCount");
  const filteredCountEl = $("#filteredCount");
  const todayCountEl    = $("#todayCount");
  const lastUpdatedEl   = $("#lastUpdated");
  const themeToggle     = $("#themeToggle");
  const modal           = $("#modal");
  const modalBackdrop   = $("#modalBackdrop");
  const modalClose      = $("#modalClose");
  const filterToggle    = $("#filterToggle");
  const sidebar         = $("#sidebar");

  // ©¤©¤ Initialize ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function init() {
    // Load papers data (injected by build script)
    if (typeof PAPERS_DATA !== "undefined") {
      allPapers = PAPERS_DATA.papers || [];
      totalCountEl.textContent = PAPERS_DATA.total_count || allPapers.length;

      if (PAPERS_DATA.last_updated) {
        const d = new Date(PAPERS_DATA.last_updated);
        lastUpdatedEl.textContent = `Last updated: ${d.toLocaleDateString("en-US", {
          year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
        })}`;
      }

      latestPaperId = findLatestPaperId(allPapers);
      if (todayCountEl) {
        todayCountEl.textContent = countPapersOnDate(allPapers, new Date());
      }
    }

    initTheme();
    initFilters();
    parseURLParams();
    applyFilters();
    bindEvents();
  }

  // ©¤©¤ Theme ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved) {
      document.documentElement.setAttribute("data-theme", saved);
    }
    // Default is light theme (set in HTML), no auto-dark
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  }

  // ©¤©¤ Build filter options ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function initFilters() {
    const years = new Set();
    const months = new Set();
    const tagCounts = {};

    allPapers.forEach((p) => {
      if (p.published) {
        const d = new Date(p.published);
        years.add(d.getFullYear());
        months.add(d.getMonth() + 1);
      }
      (p.tags || []).forEach((t) => {
        tagCounts[t] = (tagCounts[t] || 0) + 1;
      });
    });

    // Year dropdown
    [...years].sort((a, b) => b - a).forEach((y) => {
      const opt = document.createElement("option");
      opt.value = y;
      opt.textContent = y;
      yearFilter.appendChild(opt);
    });

    // Month dropdown
    const monthNames = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    [...months].sort((a, b) => a - b).forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = monthNames[m];
      monthFilter.appendChild(opt);
    });

    // Tag badges
    const sortedTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
    sortedTags.forEach(([tag, count]) => {
      const badge = document.createElement("span");
      badge.className = "tag-badge";
      badge.dataset.tag = tag;
      badge.innerHTML = `${tag} <span class="tag-count">${count}</span>`;
      badge.addEventListener("click", () => {
        if (activeTags.has(tag)) {
          activeTags.delete(tag);
          badge.classList.remove("active");
        } else {
          activeTags.add(tag);
          badge.classList.add("active");
        }
        clearTagsBtn.style.display = activeTags.size > 0 ? "inline" : "none";
        applyFilters();
        syncURL();
      });
      tagFilterEl.appendChild(badge);
    });
  }

  // ©¤©¤ Filtering & Sorting ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function applyFilters() {
    const query = activeSearchQuery.toLowerCase().trim();

    filteredPapers = allPapers.filter((p) => {
      // Search
      if (query) {
        const haystack = `${p.title} ${p.authors?.join(" ")} ${p.abstract}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }

      // Year
      if (activeYear && p.published) {
        const y = new Date(p.published).getFullYear();
        if (y !== parseInt(activeYear)) return false;
      }

      // Month
      if (activeMonth && p.published) {
        const m = new Date(p.published).getMonth() + 1;
        if (m !== parseInt(activeMonth)) return false;
      }

      // Tags (OR logic ¡ª paper must have at least one active tag)
      if (activeTags.size > 0) {
        const paperTags = new Set(p.tags || []);
        let hasAny = false;
        for (const t of activeTags) {
          if (paperTags.has(t)) { hasAny = true; break; }
        }
        if (!hasAny) return false;
      }

      return true;
    });

    // Sort
    sortPapers();

    // Reset pagination & render
    displayedCount = 0;
    paperList.innerHTML = "";
    renderNextBatch();

    filteredCountEl.textContent = filteredPapers.length;
    noResults.style.display = filteredPapers.length === 0 ? "flex" : "none";
  }

  function sortPapers() {
    switch (activeSort) {
      case "date-desc":
        filteredPapers.sort((a, b) => (b.published || "").localeCompare(a.published || ""));
        break;
      case "date-asc":
        filteredPapers.sort((a, b) => (a.published || "").localeCompare(b.published || ""));
        break;
      case "title-asc":
        filteredPapers.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
        break;
      case "title-desc":
        filteredPapers.sort((a, b) => (b.title || "").localeCompare(a.title || ""));
        break;
    }
  }

  // ©¤©¤ Render ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function renderNextBatch() {
    const end = Math.min(displayedCount + PAGE_SIZE, filteredPapers.length);
    const fragment = document.createDocumentFragment();

    for (let i = displayedCount; i < end; i++) {
      fragment.appendChild(createPaperCard(filteredPapers[i], i));
    }

    paperList.appendChild(fragment);
    displayedCount = end;

    loadMoreWrap.style.display = displayedCount < filteredPapers.length ? "block" : "none";
  }

  function createPaperCard(paper, index) {
    const card = document.createElement("article");
    card.className = "paper-card";
    card.dataset.index = index;

    const dateStr = paper.published
      ? new Date(paper.published).toLocaleDateString("en-US", {
          year: "numeric", month: "short", day: "numeric"
        })
      : "";

    const authorsStr = (paper.authors || []).slice(0, 5).join(", ") +
      (paper.authors?.length > 5 ? " et al." : "");

    const tagsHTML = (paper.tags || [])
      .map((t) => `<span class="paper-tag">${t}</span>`)
      .join("");

    const isLatest = latestPaperId && paper.id === latestPaperId;
    if (isLatest) {
      card.classList.add("is-latest");
    }

    const safeTitle = escapeHTML(paper.title);
    const latestBadgeHTML = isLatest
      ? `<div class="latest-badge">Latest</div>`
      : "";
    const figureHTML = paper.method_fig_url
      ? `<div class="paper-figure"><img src="${paper.method_fig_url}" alt="Method figure for ${safeTitle}" loading="lazy" /></div>`
      : "";

    card.innerHTML = `
      ${latestBadgeHTML}
      ${figureHTML}
      <h3 class="paper-title">${safeTitle}</h3>
      <div class="paper-authors">${escapeHTML(authorsStr)}</div>
      <div class="paper-date">${dateStr}</div>
      <p class="paper-abstract-preview">${escapeHTML(paper.abstract || "")}</p>
      <div class="paper-tags">${tagsHTML}</div>
      <div class="paper-links">
        <a href="${paper.pdf_url || "#"}" target="_blank" rel="noopener" class="paper-link" onclick="event.stopPropagation()">PDF</a>
        <a href="${paper.abs_url || "#"}" target="_blank" rel="noopener" class="paper-link" onclick="event.stopPropagation()">arXiv</a>
      </div>
    `;

    card.addEventListener("click", () => openModal(paper));
    return card;
  }

  // ©¤©¤ Modal ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function openModal(paper) {
    const dateStr = paper.published
      ? new Date(paper.published).toLocaleDateString("en-US", {
          year: "numeric", month: "long", day: "numeric"
        })
      : "";

    const updatedStr = paper.updated
      ? new Date(paper.updated).toLocaleDateString("en-US", {
          year: "numeric", month: "long", day: "numeric"
        })
      : "";

    const authors = (paper.authors || []).join(", ");
    const categories = (paper.categories || []).join(", ");

    $("#modalTitle").textContent = paper.title;
    $("#modalMeta").innerHTML = `
      <div><strong>Authors:</strong> ${escapeHTML(authors)}</div>
      <div><strong>Published:</strong> ${dateStr}${updatedStr && updatedStr !== dateStr ? ` ¡¤ Updated: ${updatedStr}` : ""}</div>
      <div><strong>Categories:</strong> ${escapeHTML(categories)}</div>
      <div><strong>ID:</strong> ${escapeHTML(paper.id || "")}</div>
    `;

    $("#modalTags").innerHTML = (paper.tags || [])
      .map((t) => `<span class="paper-tag">${t}</span>`)
      .join("");

    const figureSection = $("#modalFigureSection");
    const figureImg = $("#modalFigure");
    const figureCaption = $("#modalFigureCaption");
    if (paper.method_fig_url) {
      figureSection.style.display = "block";
      figureImg.src = paper.method_fig_url;
      figureImg.alt = `Method figure for ${paper.title}`;
      if (paper.method_fig_caption) {
        figureCaption.textContent = paper.method_fig_caption;
        figureCaption.style.display = "block";
      } else {
        figureCaption.textContent = "";
        figureCaption.style.display = "none";
      }
    } else {
      figureSection.style.display = "none";
      figureImg.removeAttribute("src");
      figureImg.alt = "";
      figureCaption.textContent = "";
      figureCaption.style.display = "none";
    }

    $("#modalAbstract").textContent = paper.abstract || "";
    $("#modalPdf").href = paper.pdf_url || "#";
    $("#modalArxiv").href = paper.abs_url || "#";

    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.style.display = "none";
    document.body.style.overflow = "";
  }

  // ©¤©¤ URL Sync ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function syncURL() {
    const params = new URLSearchParams();
    if (activeSearchQuery) params.set("q", activeSearchQuery);
    if (activeYear) params.set("year", activeYear);
    if (activeMonth) params.set("month", activeMonth);
    if (activeTags.size > 0) params.set("tags", [...activeTags].join(","));
    if (activeSort !== "date-desc") params.set("sort", activeSort);

    const search = params.toString();
    const url = search ? `?${search}` : window.location.pathname;
    history.replaceState(null, "", url);
  }

  function parseURLParams() {
    const params = new URLSearchParams(window.location.search);

    if (params.has("q")) {
      activeSearchQuery = params.get("q");
      searchInput.value = activeSearchQuery;
    }

    if (params.has("year")) {
      activeYear = params.get("year");
      yearFilter.value = activeYear;
    }

    if (params.has("month")) {
      activeMonth = params.get("month");
      monthFilter.value = activeMonth;
    }

    if (params.has("tags")) {
      params.get("tags").split(",").forEach((t) => {
        activeTags.add(t);
      });
      // Mark active tag badges after they're created
      setTimeout(() => {
        $$(".tag-badge").forEach((el) => {
          if (activeTags.has(el.dataset.tag)) {
            el.classList.add("active");
          }
        });
        clearTagsBtn.style.display = activeTags.size > 0 ? "inline" : "none";
      }, 0);
    }

    if (params.has("sort")) {
      activeSort = params.get("sort");
      sortSelect.value = activeSort;
    }
  }

  // ©¤©¤ Events ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function bindEvents() {
    // Search with debounce
    let searchTimer;
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        activeSearchQuery = searchInput.value;
        applyFilters();
        syncURL();
      }, 300);
    });

    // Keyboard shortcut: / to focus search
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
      if (e.key === "Escape") {
        if (modal.style.display === "flex") {
          closeModal();
        } else {
          searchInput.blur();
        }
      }
    });

    // Year filter
    yearFilter.addEventListener("change", () => {
      activeYear = yearFilter.value;
      applyFilters();
      syncURL();
    });

    // Month filter
    monthFilter.addEventListener("change", () => {
      activeMonth = monthFilter.value;
      applyFilters();
      syncURL();
    });

    // Sort
    sortSelect.addEventListener("change", () => {
      activeSort = sortSelect.value;
      applyFilters();
      syncURL();
    });

    // Clear tags
    clearTagsBtn.addEventListener("click", () => {
      activeTags.clear();
      $$(".tag-badge").forEach((el) => el.classList.remove("active"));
      clearTagsBtn.style.display = "none";
      applyFilters();
      syncURL();
    });

    // Load more
    loadMoreBtn.addEventListener("click", renderNextBatch);

    // Theme toggle
    themeToggle.addEventListener("click", toggleTheme);

    // Modal close
    modalClose.addEventListener("click", closeModal);
    modalBackdrop.addEventListener("click", closeModal);

    // Mobile sidebar toggle
    filterToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });

    // Close sidebar on outside click (mobile)
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("open") &&
          !sidebar.contains(e.target) &&
          !filterToggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ©¤©¤ Helpers ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  function getLocalDateKey(date) {
    return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
  }

  function countPapersOnDate(papers, targetDate) {
    const targetKey = getLocalDateKey(targetDate);
    let count = 0;
    papers.forEach((p) => {
      if (!p.published) return;
      const d = new Date(p.published);
      if (Number.isNaN(d.getTime())) return;
      if (getLocalDateKey(d) === targetKey) count += 1;
    });
    return count;
  }

  function findLatestPaperId(papers) {
    let latestId = null;
    let latestTime = -Infinity;
    papers.forEach((p) => {
      if (!p.published) return;
      const t = Date.parse(p.published);
      if (Number.isNaN(t)) return;
      if (t > latestTime) {
        latestTime = t;
        latestId = p.id || null;
      }
    });
    return latestId;
  }

  function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Expose resetFilters to global for inline onclick
  window.resetFilters = function () {
    searchInput.value = "";
    activeSearchQuery = "";
    yearFilter.value = "";
    activeYear = "";
    monthFilter.value = "";
    activeMonth = "";
    sortSelect.value = "date-desc";
    activeSort = "date-desc";
    activeTags.clear();
    $$(".tag-badge").forEach((el) => el.classList.remove("active"));
    clearTagsBtn.style.display = "none";
    applyFilters();
    syncURL();
  };

  // ©¤©¤ Boot ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
