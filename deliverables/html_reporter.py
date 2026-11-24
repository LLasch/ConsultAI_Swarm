"""
html_reporter.py — Self-contained HTML report generator for Consulting Swarm.

Replaces slide_builder.py with a single fully self-contained .html file per case.
Chart.js is fetched and cached on first use; a pure-SVG fallback is used if unavailable.
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chart.js cache
# ---------------------------------------------------------------------------

_CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"
_CHARTJS_CACHE = Path(__file__).parent / "_chartjs_cache.js"


def _get_chartjs() -> str | None:
    """Return Chart.js source string, fetching and caching if necessary."""
    if _CHARTJS_CACHE.exists():
        try:
            return _CHARTJS_CACHE.read_text(encoding="utf-8")
        except Exception:
            pass

    try:
        with urllib.request.urlopen(_CHARTJS_CDN, timeout=10) as resp:
            source = resp.read().decode("utf-8")
        try:
            _CHARTJS_CACHE.write_text(source, encoding="utf-8")
        except Exception:
            pass
        return source
    except Exception as exc:
        logger.warning("Chart.js fetch failed (%s); using SVG fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# HTML escaping helper
# ---------------------------------------------------------------------------

h = lambda s: html.escape(str(s or ""))


# ---------------------------------------------------------------------------
# CSS (plain string — no f-string so curly braces are safe)
# ---------------------------------------------------------------------------

_CSS = """
/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.6;
}

/* ── Navbar ── */
#top-navbar {
  position: sticky;
  top: 0;
  z-index: 200;
  height: 60px;
  background: #0f1b2d;
  color: #f1f5f9;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
#top-navbar .nav-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #e2e8f0;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#top-navbar .nav-meta {
  font-size: 0.78rem;
  color: #94a3b8;
  white-space: nowrap;
}
#top-navbar .btn-export {
  background: #1d4ed8;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}
#top-navbar .btn-export:hover { background: #1e40af; }

/* ── Layout ── */
#layout {
  display: flex;
  min-height: calc(100vh - 60px);
}

/* ── Sidebar ── */
#sidebar {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 60px;
  height: calc(100vh - 60px);
  overflow-y: auto;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  padding: 20px 0 40px;
}
#sidebar .sidebar-mini-stat {
  padding: 10px 18px 14px;
  font-size: 0.75rem;
  color: #64748b;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 8px;
  line-height: 1.8;
}
#sidebar .sidebar-mini-stat strong {
  color: #1d4ed8;
  font-weight: 700;
}
#sidebar nav a {
  display: block;
  padding: 7px 20px;
  font-size: 0.82rem;
  color: #475569;
  text-decoration: none;
  border-left: 3px solid transparent;
  transition: color 0.12s, border-color 0.12s, background 0.12s;
}
#sidebar nav a:hover {
  color: #1d4ed8;
  background: #f1f5f9;
}
#sidebar nav a.active {
  color: #1d4ed8;
  font-weight: 600;
  border-left-color: #1d4ed8;
  background: #eff6ff;
}

/* ── Main content ── */
#main-content {
  flex: 1;
  min-width: 0;
  padding: 32px 36px 60px;
  max-width: 960px;
}

/* ── Section ── */
.report-section {
  margin-bottom: 28px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  user-select: none;
  transition: background 0.12s;
}
.section-header:hover { background: #f8fafc; }
.section-header h2 {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  flex: 1;
}
.section-chevron {
  font-size: 0.9rem;
  color: #94a3b8;
  transition: transform 0.2s;
}
.report-section.is-open .section-chevron { transform: rotate(0deg); }
.report-section:not(.is-open) .section-chevron { transform: rotate(-90deg); }

.section-body {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 20px 24px;
  overflow: hidden;
  transition: max-height 0.3s ease, padding 0.3s ease;
}
.report-section.is-open .section-body { max-height: 9999px; }
.report-section:not(.is-open) .section-body { max-height: 0; padding-top: 0; padding-bottom: 0; }

/* Executive summary — no collapsible chrome */
#section-executive .section-header { cursor: default; }
#section-executive .section-header:hover { background: #fff; }
#section-executive .section-chevron { display: none; }

/* ── Stat cards ── */
.stat-cards {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
  min-width: 120px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 20px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-card .stat-number {
  font-size: 2rem;
  font-weight: 800;
  color: #1d4ed8;
  line-height: 1.1;
}
.stat-card .stat-label {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* ── Summary text & bottom-line ── */
.summary-text {
  color: #334155;
  margin-bottom: 16px;
}
.bottom-line-box {
  border-left: 4px solid #1d4ed8;
  background: #eff6ff;
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
  color: #1e3a8a;
  font-style: italic;
  font-size: 0.92rem;
}

/* ── Problem statement ── */
.problem-text {
  color: #334155;
  margin-bottom: 14px;
}
.framework-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 0.88rem;
  color: #475569;
  margin-bottom: 12px;
}
.missing-info {
  font-size: 0.82rem;
  color: #64748b;
  background: #fefce8;
  border: 1px solid #fef08a;
  border-radius: 6px;
  padding: 8px 12px;
}

/* ── Findings ── */
.finding-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.finding-title {
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 8px;
}
.confidence-bar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.confidence-bar-bg {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}
.confidence-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s;
}
.confidence-bar-fill.green { background: #16a34a; }
.confidence-bar-fill.amber { background: #f59e0b; }
.confidence-bar-fill.red   { background: #dc2626; }
.confidence-label {
  font-size: 0.78rem;
  font-weight: 700;
  min-width: 36px;
  text-align: right;
}
.confidence-label.green { color: #16a34a; }
.confidence-label.amber { color: #f59e0b; }
.confidence-label.red   { color: #dc2626; }
.finding-evidence {
  font-size: 0.84rem;
  color: #64748b;
}

/* ── Recommendations ── */
.rec-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.rec-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  background: #fff;
  border-left: 4px solid #1d4ed8;
  user-select: none;
  transition: background 0.12s;
}
.rec-card-header:hover { background: #f8fafc; }
.rec-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d4ed8;
  color: #fff;
  font-weight: 700;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.rec-title {
  flex: 1;
  font-weight: 600;
  color: #0f172a;
  font-size: 0.95rem;
}
.chip {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  background: #e0f2fe;
  color: #075985;
  white-space: nowrap;
}
.chip.support { background: #dcfce7; color: #166534; }
.chip.score { background: #f1f5f9; color: #475569; }
.rec-chevron { font-size: 0.85rem; color: #94a3b8; transition: transform 0.2s; }
.rec-card.is-open .rec-chevron { transform: rotate(0deg); }
.rec-card:not(.is-open) .rec-chevron { transform: rotate(-90deg); }

.rec-card-body {
  overflow: hidden;
  transition: max-height 0.3s ease, padding 0.3s ease;
  padding: 0 18px;
  background: #fafafa;
  border-top: 1px solid #e2e8f0;
}
.rec-card.is-open .rec-card-body { max-height: 2000px; padding: 16px 18px; }
.rec-card:not(.is-open) .rec-card-body { max-height: 0; }

.rec-detail-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
  font-weight: 700;
  margin-top: 12px;
  margin-bottom: 4px;
}
.rec-detail-label:first-child { margin-top: 0; }
.rec-detail-text { font-size: 0.88rem; color: #334155; }
.rec-steps { font-size: 0.88rem; color: #334155; padding-left: 20px; }
.rec-steps li { margin-bottom: 4px; }

/* ── Financial ── */
.chart-container {
  position: relative;
  width: 100%;
  margin-bottom: 20px;
}
.financial-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-top: 12px;
}
.financial-table th {
  background: #f1f5f9;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
}
.financial-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}

/* ── Risk ── */
.risk-stat-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.risk-stat-banner.low { background: #f0fdf4; border-color: #bbf7d0; }
.risk-stat-banner.medium { background: #fffbeb; border-color: #fde68a; }
.risk-stat-banner.high { background: #fff7ed; border-color: #fed7aa; }
.risk-stat-banner.critical { background: #fef2f2; border-color: #fecaca; }
.risk-label-big {
  font-weight: 800;
  font-size: 1.1rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.risk-label-big.low { color: #16a34a; }
.risk-label-big.medium { color: #d97706; }
.risk-label-big.high { color: #ea580c; }
.risk-label-big.critical { color: #dc2626; }

.vuln-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.severity-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 6px;
}
.severity-badge.critical { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.severity-badge.high     { background: #fff7ed; color: #f97316; border: 1px solid #fed7aa; }
.severity-badge.medium   { background: #fffbeb; color: #f59e0b; border: 1px solid #fde68a; }
.severity-badge.low      { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }

.vuln-title { font-weight: 600; color: #0f172a; margin-bottom: 6px; }
.vuln-text { font-size: 0.87rem; color: #475569; margin-bottom: 6px; }
.vuln-mitigation { font-size: 0.82rem; color: #64748b; font-style: italic; }

/* ── Roadmap ── */
.roadmap-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.phase-column {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.phase-header {
  padding: 10px 14px;
  font-weight: 700;
  font-size: 0.82rem;
  color: #fff;
}
.phase-header.p1 { background: #1d4ed8; }
.phase-header.p2 { background: #7c3aed; }
.phase-header.p3 { background: #0891b2; }
.phase-body {
  padding: 12px 14px;
  background: #fff;
}
.phase-body ul {
  list-style: none;
  padding: 0;
}
.phase-body li {
  font-size: 0.85rem;
  color: #334155;
  padding: 4px 0 4px 14px;
  position: relative;
  border-bottom: 1px solid #f8fafc;
}
.phase-body li::before {
  content: "▸";
  position: absolute;
  left: 0;
  color: #94a3b8;
  font-size: 0.7rem;
  top: 6px;
}

/* ── Pushback ── */
.callout-box {
  border-left: 4px solid #f59e0b;
  background: #fffbeb;
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
  color: #78350f;
  margin-bottom: 16px;
  font-size: 0.9rem;
}
.pushback-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.pushback-rec { font-weight: 600; color: #0f172a; margin-bottom: 6px; }
.pushback-objection { font-size: 0.87rem; color: #dc2626; margin-bottom: 4px; }
.pushback-response { font-size: 0.85rem; color: #475569; }

/* ── Dissenting ── */
.quote-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 10px;
  background: #fafafa;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.quote-text {
  font-style: italic;
  color: #475569;
  margin-bottom: 8px;
  border-left: 3px solid #cbd5e1;
  padding-left: 12px;
}
.quote-source { font-size: 0.78rem; color: #94a3b8; }

/* ── Methodology ── */
.method-bullets {
  list-style: none;
  padding: 0;
  margin-bottom: 16px;
}
.method-bullets li {
  padding: 5px 0;
  font-size: 0.87rem;
  color: #475569;
  border-bottom: 1px solid #f1f5f9;
}
.expertise-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.expertise-chip {
  background: #f1f5f9;
  border-radius: 999px;
  padding: 3px 11px;
  font-size: 0.78rem;
  color: #475569;
}
.tag-chip {
  display: inline-block;
  background: #ede9fe;
  color: #4c1d95;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.75rem;
  margin: 2px;
}
.model-footnote {
  font-size: 0.78rem;
  color: #94a3b8;
  margin-top: 12px;
  font-family: 'Courier New', monospace;
}

/* ── Mobile horizontal nav ── */
#mobile-nav {
  display: none;
  position: sticky;
  top: 60px;
  z-index: 150;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  overflow-x: auto;
  white-space: nowrap;
  padding: 0 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}
#mobile-nav a {
  display: inline-block;
  padding: 10px 12px;
  font-size: 0.78rem;
  color: #475569;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 0.12s, border-color 0.12s;
}
#mobile-nav a.active {
  color: #1d4ed8;
  border-bottom-color: #1d4ed8;
  font-weight: 600;
}

/* ── Print ── */
@media print {
  #top-navbar .btn-export { display: none; }
  #sidebar { display: none; }
  #mobile-nav { display: none; }
  #main-content {
    margin-left: 0 !important;
    padding: 12px 16px;
    max-width: 100%;
  }
  #layout { display: block; }
  .report-section .section-body {
    max-height: none !important;
    padding: 16px 20px !important;
    display: block !important;
  }
  .rec-card .rec-card-body {
    max-height: none !important;
    padding: 14px 18px !important;
    display: block !important;
  }
  .section-header { cursor: default; break-after: avoid; }
  .stat-card { break-inside: avoid; }
  .finding-card, .rec-card, .vuln-card { break-inside: avoid; }
  .roadmap-grid { grid-template-columns: repeat(3, 1fr); }
  body { font-size: 13px; }
  @page { margin: 1.5cm 1.5cm; }
}

/* ── Chart plan blocks ── */
.chart-plan-block {
  margin: 24px 0;
}
.chart-plan-title {
  font-weight: 700;
  font-size: 0.95rem;
  color: #0f172a;
  margin-bottom: 6px;
}
.chart-plan-annotation {
  font-size: 0.82rem;
  color: #64748b;
  margin-top: 8px;
  font-style: italic;
  border-left: 3px solid #e2e8f0;
  padding-left: 8px;
}
.chart-plan-canvas-wrap {
  position: relative;
  height: 280px;
}

/* ── Stat callout ── */
.stat-callout {
  background: #1d4ed8;
  border-radius: 10px;
  padding: 24px 32px;
  margin: 20px 0;
  display: inline-block;
  min-width: 200px;
  text-align: center;
}
.stat-callout .callout-number {
  font-size: 3.5rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.1;
}
.stat-callout .callout-caption {
  font-size: 0.88rem;
  color: #bfdbfe;
  margin-top: 6px;
}

/* ── Responsive ── */
@media (max-width: 767px) {
  #sidebar { display: none; }
  #mobile-nav { display: block; }
  #main-content { padding: 16px; margin-left: 0 !important; }
  .roadmap-grid { grid-template-columns: 1fr; }
  .stat-cards { gap: 10px; }
  .stat-card { min-width: 100px; }
  .chart-plan-canvas-wrap { height: 220px; }
}
"""

# ---------------------------------------------------------------------------
# JS (plain string — placeholder __REPORT_DATA__ is replaced at generation time)
# ---------------------------------------------------------------------------

_JS_TEMPLATE = r"""
(function () {
  "use strict";

  var DATA = __REPORT_DATA__;

  /* ── Collapsible sections ── */
  document.querySelectorAll(".section-header[data-target]").forEach(function (hdr) {
    hdr.addEventListener("click", function () {
      var sec = document.getElementById(hdr.dataset.target);
      if (!sec) return;
      sec.classList.toggle("is-open");
    });
  });

  /* ── Collapsible rec cards ── */
  document.querySelectorAll(".rec-card-header").forEach(function (hdr) {
    hdr.addEventListener("click", function () {
      hdr.closest(".rec-card").classList.toggle("is-open");
    });
  });

  /* ── Export PDF ── */
  document.getElementById("btn-export-pdf").addEventListener("click", function () {
    /* expand all sections */
    document.querySelectorAll(".report-section").forEach(function (s) {
      s.classList.add("is-open");
    });
    document.querySelectorAll(".rec-card").forEach(function (c) {
      c.classList.add("is-open");
    });
    setTimeout(function () { window.print(); }, 150);
  });

  /* ── Sidebar active on scroll ── */
  var navLinks = document.querySelectorAll("#sidebar nav a, #mobile-nav a");
  var sections = [];
  navLinks.forEach(function (link) {
    var id = link.getAttribute("href").replace("#", "");
    var el = document.getElementById(id);
    if (el) sections.push({ id: id, el: el });
  });

  function setActive(id) {
    navLinks.forEach(function (link) {
      if (link.getAttribute("href") === "#" + id) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });
  }

  if ("IntersectionObserver" in window && sections.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    sections.forEach(function (s) { observer.observe(s.el); });
  }

  /* ── Charts ── */
  if (typeof Chart === "undefined") return;

  /* Financial chart */
  var finCanvas = document.getElementById("chart-financial");
  if (finCanvas && DATA.financial && DATA.financial.labels && DATA.financial.labels.length) {
    var finData = DATA.financial;
    var datasets = [];
    if (finData.conservative && finData.conservative.length) {
      datasets.push({
        label: "Conservative",
        data: finData.conservative,
        backgroundColor: "#94a3b8"
      });
    }
    if (finData.base && finData.base.length) {
      datasets.push({
        label: "Base",
        data: finData.base,
        backgroundColor: "#1d4ed8"
      });
    }
    if (finData.optimistic && finData.optimistic.length) {
      datasets.push({
        label: "Optimistic",
        data: finData.optimistic,
        backgroundColor: "#60a5fa"
      });
    }
    if (datasets.length === 0 && finData.base && finData.base.length) {
      datasets.push({ label: "Value", data: finData.base, backgroundColor: "#1d4ed8" });
    }
    new Chart(finCanvas, {
      type: "bar",
      data: { labels: finData.labels, datasets: datasets },
      options: {
        responsive: true,
        plugins: { legend: { position: "top" } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  /* Confidence chart */
  var confCanvas = document.getElementById("chart-confidence");
  if (confCanvas && DATA.confidence && DATA.confidence.labels && DATA.confidence.labels.length) {
    var confData = DATA.confidence;
    var colors = confData.values.map(function (v) {
      return v >= 0.8 ? "#16a34a" : v >= 0.6 ? "#f59e0b" : "#dc2626";
    });
    new Chart(confCanvas, {
      type: "bar",
      data: {
        labels: confData.labels,
        datasets: [{
          label: "Confidence %",
          data: confData.values.map(function (v) { return Math.round(v * 100); }),
          backgroundColor: colors,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, max: 100 } }
      }
    });
  }

  /* ── Planned charts from chart planner ── */
  var CHART_SPECS = __CHART_SPECS__;
  var PALETTE = [
    "#1d4ed8", "#60a5fa", "#16a34a", "#f59e0b",
    "#dc2626", "#94a3b8", "#7c3aed", "#0891b2"
  ];

  CHART_SPECS.forEach(function (spec) {
    if (!spec || !spec.id) return;
    if (spec.chart_type === "stat_callout") return; // rendered as static HTML

    var canvas = document.getElementById("chart-plan-" + spec.id);
    if (!canvas) return;

    var data = spec.data || {};
    var labels = data.labels || [];
    var values = data.values || [];
    var chartType = spec.chart_type || "bar";
    var datasets = [];
    var options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { size: 12 } } }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    };

    if (chartType === "waterfall") {
      /* Stacked bar with transparent base — standard Chart.js waterfall workaround */
      var bases = [];
      var segments = [];
      var segColors = [];
      var running = 0;
      for (var wi = 0; wi < values.length; wi++) {
        var v = values[wi] || 0;
        if (wi === 0) {
          bases.push(0);
          segments.push(v);
          segColors.push("#94a3b8");
        } else {
          var base = running;
          var delta = v;
          bases.push(delta >= 0 ? base : base + delta);
          segments.push(Math.abs(delta));
          segColors.push(delta >= 0 ? "#16a34a" : "#dc2626");
        }
        running += v;
      }
      datasets = [
        {
          label: "",
          data: bases,
          backgroundColor: "rgba(0,0,0,0)",
          borderWidth: 0,
          stack: "wf"
        },
        {
          label: "Impact",
          data: segments,
          backgroundColor: segColors,
          borderRadius: 4,
          stack: "wf"
        }
      ];
      chartType = "bar";
      options.plugins.legend = { display: false };
      options.scales = {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: false, grid: { color: "#f1f5f9" } }
      };

    } else if (chartType === "doughnut") {
      datasets = [{
        data: values,
        backgroundColor: PALETTE.slice(0, values.length),
        borderWidth: 2,
        borderColor: "#fff"
      }];
      delete options.scales;
      options.plugins.legend = { position: "right", labels: { boxWidth: 14, font: { size: 12 } } };

    } else if (chartType === "comparison" || (data.datasets && data.datasets.length)) {
      var rawDs = data.datasets || [];
      datasets = rawDs.map(function (ds, di) {
        return {
          label: ds.label || ("Series " + (di + 1)),
          data: ds.values || ds.data || [],
          backgroundColor: PALETTE[di % PALETTE.length],
          borderColor: PALETTE[di % PALETTE.length],
          borderRadius: 4,
          tension: 0.3
        };
      });
      chartType = (chartType === "comparison") ? "bar" : chartType;

    } else if (chartType === "line" || chartType === "timeline") {
      datasets = [{
        label: spec.title || "Trend",
        data: values,
        borderColor: PALETTE[0],
        backgroundColor: PALETTE[0] + "22",
        tension: 0.35,
        fill: true,
        pointRadius: 5,
        pointBackgroundColor: PALETTE[0]
      }];
      chartType = "line";
      options.plugins.legend = { display: false };

    } else if (chartType === "horizontal_bar" || chartType === "funnel") {
      datasets = [{
        label: spec.title || "Value",
        data: values,
        backgroundColor: values.map(function (v, vi) { return PALETTE[vi % PALETTE.length]; }),
        borderRadius: 4
      }];
      chartType = "bar";
      options.indexAxis = "y";
      options.scales = {
        x: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        y: { grid: { display: false } }
      };
      options.plugins.legend = { display: false };

    } else {
      /* default: vertical bar */
      datasets = [{
        label: spec.title || "Value",
        data: values,
        backgroundColor: PALETTE[0],
        borderRadius: 4
      }];
      options.plugins.legend = { display: false };
    }

    new Chart(canvas, {
      type: chartType,
      data: { labels: labels, datasets: datasets },
      options: options
    });
  });

})();
"""


# ---------------------------------------------------------------------------
# SVG fallback chart generators
# ---------------------------------------------------------------------------

def _svg_hbar(items: list[tuple[str, float]], width: int = 560, bar_height: int = 28, gap: int = 10) -> str:
    """Generate a simple horizontal bar SVG. items = [(label, value 0-1), ...]."""
    if not items:
        return ""
    max_val = max(v for _, v in items) or 1.0
    label_w = 180
    value_w = 50
    chart_w = width - label_w - value_w - 20
    row_h = bar_height + gap
    total_h = len(items) * row_h + 20

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_h}" '
        f'style="width:100%;font-family:system-ui,-apple-system,sans-serif">'
    ]
    for i, (label, val) in enumerate(items):
        y = 10 + i * row_h
        bar_w = max(4, int((val / max_val) * chart_w))
        if val >= 0.8:
            color = "#16a34a"
        elif val >= 0.6:
            color = "#f59e0b"
        else:
            color = "#dc2626"
        short_label = label[:32] + "…" if len(label) > 32 else label
        esc_label = html.escape(short_label)
        pct = f"{val * 100:.0f}%"
        lines.append(
            f'  <text x="{label_w - 6}" y="{y + bar_height * 0.7}" '
            f'text-anchor="end" font-size="12" fill="#475569">{esc_label}</text>'
        )
        lines.append(
            f'  <rect x="{label_w}" y="{y}" width="{bar_w}" height="{bar_height}" '
            f'rx="4" fill="{color}" />'
        )
        lines.append(
            f'  <text x="{label_w + bar_w + 6}" y="{y + bar_height * 0.7}" '
            f'font-size="12" fill="#334155">{pct}</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def _svg_grouped_bar(labels: list[str], groups: dict[str, list[float]], width: int = 580) -> str:
    """Generate a grouped bar SVG for financial data."""
    if not labels or not groups:
        return ""
    group_names = list(groups.keys())
    n_groups = len(group_names)
    n_labels = len(labels)

    bar_w = 28
    group_w = n_groups * bar_w + 12
    left_pad = 60
    bottom_pad = 60
    top_pad = 20
    chart_inner_w = max(width - left_pad - 20, n_labels * group_w + 20)
    all_vals = [v for vals in groups.values() for v in vals if v is not None]
    max_val = max(all_vals) if all_vals else 1.0
    chart_h = 200
    total_h = chart_h + top_pad + bottom_pad
    total_w = chart_inner_w + left_pad + 20

    colors_map = {
        "conservative": "#94a3b8",
        "base": "#1d4ed8",
        "optimistic": "#60a5fa",
    }
    default_colors = ["#1d4ed8", "#94a3b8", "#60a5fa", "#f59e0b"]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'style="width:100%;font-family:system-ui,-apple-system,sans-serif">'
    ]

    # Y-axis line
    lines.append(
        f'<line x1="{left_pad}" y1="{top_pad}" x2="{left_pad}" '
        f'y2="{top_pad + chart_h}" stroke="#e2e8f0" stroke-width="1"/>'
    )

    for li, label in enumerate(labels):
        group_x = left_pad + li * group_w + 6
        for gi, gname in enumerate(group_names):
            vals = groups[gname]
            val = vals[li] if li < len(vals) else 0.0
            if val is None:
                val = 0.0
            bar_pixel_h = max(2, int((val / max_val) * chart_h))
            bx = group_x + gi * bar_w
            by = top_pad + chart_h - bar_pixel_h
            color = colors_map.get(gname.lower(), default_colors[gi % len(default_colors)])
            lines.append(
                f'<rect x="{bx}" y="{by}" width="{bar_w - 3}" height="{bar_pixel_h}" '
                f'rx="3" fill="{color}"/>'
            )
        # X label
        short = label[:14] + "…" if len(label) > 14 else label
        lines.append(
            f'<text x="{group_x + group_w / 2 - 6}" y="{top_pad + chart_h + 16}" '
            f'text-anchor="middle" font-size="11" fill="#64748b">{html.escape(short)}</text>'
        )

    # Legend
    legend_x = left_pad + 6
    legend_y = top_pad + chart_h + 32
    for gi, gname in enumerate(group_names):
        color = colors_map.get(gname.lower(), default_colors[gi % len(default_colors)])
        lx = legend_x + gi * 100
        lines.append(f'<rect x="{lx}" y="{legend_y}" width="12" height="12" rx="2" fill="{color}"/>')
        lines.append(
            f'<text x="{lx + 16}" y="{legend_y + 10}" font-size="11" fill="#475569">'
            f'{html.escape(gname.capitalize())}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section builders — each returns an HTML string
# ---------------------------------------------------------------------------

def _section_wrap(section_id: str, title: str, content: str, starts_open: bool = True) -> str:
    open_cls = "is-open" if starts_open else ""
    return (
        f'<div class="report-section {open_cls}" id="{section_id}">'
        f'<div class="section-header" data-target="{section_id}">'
        f'<h2>{h(title)}</h2><span class="section-chevron">&#9662;</span>'
        f"</div>"
        f'<div class="section-body">{content}</div>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Chart-plan helpers
# ---------------------------------------------------------------------------

_PLACEMENT_MAP: dict[str, str] = {
    "executive_summary": "section-executive",
    "executive": "section-executive",
    "problem_statement": "section-problem",
    "problem": "section-problem",
    "key_findings": "section-findings",
    "findings": "section-findings",
    "recommendations": "section-recs",
    "recs": "section-recs",
    "financial_analysis": "section-financial",
    "financial": "section-financial",
    "risk_assessment": "section-risk",
    "risk": "section-risk",
    "implementation_roadmap": "section-roadmap",
    "roadmap": "section-roadmap",
}


def _render_chart_block(spec: dict) -> str:
    """Return HTML for one chart spec — canvas div for charts, styled div for stat callouts."""
    chart_id = h(str(spec.get("id") or ""))
    title = h(str(spec.get("title") or ""))
    story = h(str(spec.get("story") or ""))
    chart_type = str(spec.get("chart_type") or "bar")

    annotation_html = (
        f'<p class="chart-plan-annotation">{story}</p>' if story else ""
    )

    if chart_type == "stat_callout":
        data = spec.get("data") or {}
        raw_value = data.get("value") or (
            data.get("values", [""])[0] if data.get("values") else ""
        )
        caption = h(str(data.get("caption") or spec.get("title") or ""))
        value = h(str(raw_value))
        return (
            f'<div class="chart-plan-block">'
            f'<div class="stat-callout">'
            f'<div class="callout-number">{value}</div>'
            f'<div class="callout-caption">{caption}</div>'
            f'</div>'
            f'{annotation_html}'
            f'</div>'
        )

    title_html = f'<p class="chart-plan-title">{title}</p>' if title else ""
    return (
        f'<div class="chart-plan-block">'
        f'{title_html}'
        f'<div class="chart-plan-canvas-wrap">'
        f'<canvas id="chart-plan-{chart_id}"></canvas>'
        f'</div>'
        f'{annotation_html}'
        f'</div>'
    )


def _build_chart_blocks(chart_plan: list) -> dict:
    """Group rendered chart HTML by section placement ID."""
    blocks: dict[str, str] = {}
    for spec in (chart_plan or []):
        if not isinstance(spec, dict):
            continue
        placement = str(spec.get("placement") or "section-financial").lower().strip()
        # Accept both "section-financial" style and "financial_analysis" style
        if placement.startswith("section-"):
            section_id = placement
        else:
            section_id = _PLACEMENT_MAP.get(placement, "section-financial")
        chart_html = _render_chart_block(spec)
        blocks[section_id] = blocks.get(section_id, "") + chart_html
    return blocks


def _inject_charts_into_section(section_html: str, charts_html: str) -> str:
    """Append chart HTML inside a section body, before the two closing div tags."""
    if not section_html or not charts_html:
        return section_html
    tail = "</div></div>"
    if section_html.endswith(tail):
        return section_html[: -len(tail)] + charts_html + tail
    # Fallback: just concatenate
    return section_html + charts_html


# ---------------------------------------------------------------------------
# Section builders — each returns an HTML string
# ---------------------------------------------------------------------------

def _build_executive_summary(consensus: dict, round1_results: list, red_team: dict | None) -> str:
    n_agents = len(round1_results)
    recs = consensus.get("recommendations") or []
    findings = consensus.get("key_findings") or []
    risk_rating = (red_team or {}).get("overall_risk_rating") or consensus.get("risk_rating") or ""

    stat_cards_html = ""

    def stat_card(number, label):
        return (
            f'<div class="stat-card">'
            f'<div class="stat-number">{h(number)}</div>'
            f'<div class="stat-label">{h(label)}</div>'
            f"</div>"
        )

    stat_cards_html = (
        stat_card(str(n_agents), "Analysts")
        + stat_card(str(len(recs)), "Recommendations")
        + stat_card(str(len(findings)), "Key Findings")
    )
    if risk_rating:
        stat_cards_html += stat_card(str(risk_rating).upper(), "Risk Rating")

    exec_summary = h(consensus.get("executive_summary") or "")
    bottom_line = h(consensus.get("bottom_line") or "")

    content = f'<div class="stat-cards">{stat_cards_html}</div>'
    if exec_summary:
        content += f'<p class="summary-text">{exec_summary}</p>'
    if bottom_line:
        content += f'<div class="bottom-line-box">{bottom_line}</div>'

    # Executive summary is always open and not collapsible — use special id
    return (
        f'<div class="report-section is-open" id="section-executive">'
        f'<div class="section-header">'
        f'<h2>Executive Summary</h2><span class="section-chevron" style="visibility:hidden">&#9662;</span>'
        f"</div>"
        f'<div class="section-body">{content}</div>'
        f"</div>"
    )


def _build_problem_statement(consensus: dict) -> str:
    problem = h(consensus.get("problem_statement") or "")
    framework = h(consensus.get("analysis_framework") or "")
    missing = consensus.get("missing_information") or []
    if isinstance(missing, str):
        missing = [missing] if missing else []

    if not problem and not framework:
        return ""

    content = ""
    if problem:
        content += f'<p class="problem-text">{problem}</p>'
    if framework:
        content += f'<div class="framework-box"><strong>Analysis Framework:</strong> {framework}</div>'
    if missing:
        items_html = " &bull; ".join(h(m) for m in missing if m)
        if items_html:
            content += f'<div class="missing-info"><strong>Missing Information:</strong> {items_html}</div>'

    return _section_wrap("section-problem", "Problem Statement", content, starts_open=True)


def _conf_color(v: float) -> str:
    if v >= 0.8:
        return "green"
    if v >= 0.6:
        return "amber"
    return "red"


def _build_key_findings(consensus: dict) -> str:
    findings = consensus.get("key_findings") or []
    if not findings:
        return ""

    cards = []
    for f in findings:
        finding_text = h(f.get("finding") or "")
        evidence = h(f.get("evidence") or "")
        conf_raw = f.get("confidence", 0.7)
        try:
            conf = float(conf_raw)
        except (TypeError, ValueError):
            conf = 0.7
        conf = max(0.0, min(1.0, conf))
        color = _conf_color(conf)
        pct = f"{conf * 100:.0f}%"

        bar = (
            f'<div class="confidence-bar-wrap">'
            f'<div class="confidence-bar-bg">'
            f'<div class="confidence-bar-fill {color}" style="width:{conf*100:.0f}%"></div>'
            f"</div>"
            f'<span class="confidence-label {color}">{pct}</span>'
            f"</div>"
        )
        evidence_html = f'<p class="finding-evidence">{evidence}</p>' if evidence else ""
        cards.append(
            f'<div class="finding-card">'
            f'<div class="finding-title">{finding_text}</div>'
            f"{bar}{evidence_html}"
            f"</div>"
        )

    return _section_wrap("section-findings", "Key Findings", "".join(cards), starts_open=True)


_REC_RANK_COLORS = ["#1d4ed8", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"]


def _build_recommendations(consensus: dict) -> str:
    recs = consensus.get("recommendations") or []
    if not recs:
        return ""

    cards = []
    for i, rec in enumerate(recs):
        rank = rec.get("rank", i + 1)
        title = h(rec.get("title") or f"Recommendation {rank}")
        timeline = h(rec.get("timeline") or "")
        support = h(rec.get("panel_support") or "")
        conf_raw = rec.get("confidence_score", rec.get("confidence", ""))
        conf_display = ""
        if conf_raw != "" and conf_raw is not None:
            try:
                conf_val = float(conf_raw)
                conf_display = f"{conf_val * 100:.0f}%" if conf_val <= 1.0 else f"{conf_val:.0f}%"
            except (TypeError, ValueError):
                conf_display = h(str(conf_raw))

        description = h(rec.get("description") or "")
        rationale = h(rec.get("rationale") or "")
        steps = rec.get("implementation_steps") or rec.get("steps") or []
        if isinstance(steps, str):
            steps = [steps]
        impact = h(rec.get("expected_impact") or rec.get("impact") or "")
        risks = h(rec.get("risks_and_mitigations") or rec.get("risks") or "")

        color = _REC_RANK_COLORS[i % len(_REC_RANK_COLORS)]

        chips_html = ""
        if timeline:
            chips_html += f'<span class="chip">{timeline}</span>'
        if support:
            chips_html += f'<span class="chip support">{support}</span>'
        if conf_display:
            chips_html += f'<span class="chip score">{conf_display}</span>'

        body_parts = []
        if description:
            body_parts.append(
                f'<div class="rec-detail-label">Description</div>'
                f'<p class="rec-detail-text">{description}</p>'
            )
        if rationale:
            body_parts.append(
                f'<div class="rec-detail-label">Rationale</div>'
                f'<p class="rec-detail-text">{rationale}</p>'
            )
        if steps:
            steps_items = "".join(f"<li>{h(s)}</li>" for s in steps if s)
            body_parts.append(
                f'<div class="rec-detail-label">Implementation Steps</div>'
                f'<ol class="rec-steps">{steps_items}</ol>'
            )
        if impact:
            body_parts.append(
                f'<div class="rec-detail-label">Expected Impact</div>'
                f'<p class="rec-detail-text">{impact}</p>'
            )
        if risks:
            body_parts.append(
                f'<div class="rec-detail-label">Risks &amp; Mitigations</div>'
                f'<p class="rec-detail-text">{risks}</p>'
            )

        body_html = "".join(body_parts)
        has_body = bool(body_html)
        open_cls = "is-open" if has_body else ""

        cards.append(
            f'<div class="rec-card {open_cls}">'
            f'<div class="rec-card-header" style="border-left-color:{color}">'
            f'<div class="rec-rank" style="background:{color}">{h(str(rank))}</div>'
            f'<div class="rec-title">{title}</div>'
            f"{chips_html}"
            f'<span class="rec-chevron">&#9662;</span>'
            f"</div>"
            + (f'<div class="rec-card-body">{body_html}</div>' if has_body else "")
            + "</div>"
        )

    return _section_wrap("section-recs", "Recommendations", "".join(cards), starts_open=True)


def _build_financial(consensus: dict, quant_analysis: dict | None, chartjs_available: bool) -> str:
    recs = consensus.get("recommendations") or []
    models = (quant_analysis or {}).get("models") or {}

    if not models and not recs:
        return ""

    chart_html = ""

    if models:
        labels = list(models.keys())
        conservative = [models[k].get("conservative") for k in labels]
        base = [models[k].get("base") for k in labels]
        optimistic = [models[k].get("optimistic") for k in labels]

        def safe_floats(lst):
            result = []
            for v in lst:
                if v is None:
                    result.append(None)
                else:
                    try:
                        result.append(float(v))
                    except (TypeError, ValueError):
                        result.append(None)
            return result

        conservative = safe_floats(conservative)
        base = safe_floats(base)
        optimistic = safe_floats(optimistic)

        if chartjs_available:
            chart_html = (
                '<div class="chart-container" style="height:300px;">'
                '<canvas id="chart-financial"></canvas>'
                "</div>"
            )
        else:
            # SVG grouped bar fallback
            groups = {}
            if any(v is not None for v in conservative):
                groups["conservative"] = [v or 0.0 for v in conservative]
            if any(v is not None for v in base):
                groups["base"] = [v or 0.0 for v in base]
            if any(v is not None for v in optimistic):
                groups["optimistic"] = [v or 0.0 for v in optimistic]
            if groups:
                chart_html = _svg_grouped_bar(labels, groups)

    # Confidence chart
    findings = consensus.get("key_findings") or []
    if findings and chartjs_available:
        chart_html += (
            '<div class="chart-container" style="margin-top:20px;">'
            '<canvas id="chart-confidence"></canvas>'
            "</div>"
        )
    elif findings and not chartjs_available:
        items = []
        for f in findings:
            label = str(f.get("finding") or "")[:50]
            try:
                val = float(f.get("confidence", 0.7))
            except (TypeError, ValueError):
                val = 0.7
            items.append((label, val))
        if items:
            chart_html += "<div style='margin-top:20px;'>" + _svg_hbar(items) + "</div>"

    # Payback / ROI table
    table_rows = ""
    for name, model in models.items():
        payback = h(str(model.get("payback_period") or ""))
        roi = h(str(model.get("roi") or ""))
        if payback or roi:
            table_rows += (
                f"<tr><td>{h(name)}</td><td>{payback}</td><td>{roi}</td></tr>"
            )
    table_html = ""
    if table_rows:
        table_html = (
            '<table class="financial-table">'
            "<thead><tr><th>Recommendation</th><th>Payback Period</th><th>ROI</th></tr></thead>"
            f"<tbody>{table_rows}</tbody>"
            "</table>"
        )

    content = chart_html + table_html
    if not content:
        return ""

    return _section_wrap("section-financial", "Financial Analysis", content, starts_open=False)


def _severity_class(s: str) -> str:
    s = (s or "").lower()
    if s in ("critical",):
        return "critical"
    if s in ("high",):
        return "high"
    if s in ("medium", "moderate"):
        return "medium"
    return "low"


def _build_risk(consensus: dict, red_team: dict | None) -> str:
    rt = red_team or {}
    vulns = rt.get("vulnerabilities") or []
    overall = h(rt.get("overall_risk_rating") or consensus.get("risk_assessment") or "")
    risk_text = h(consensus.get("risk_assessment") or "")

    rating_str = (rt.get("overall_risk_rating") or "unknown").lower()
    severity_cls = _severity_class(rating_str)

    content = ""
    if overall:
        content += (
            f'<div class="risk-stat-banner {severity_cls}">'
            f'<span class="risk-label-big {severity_cls}">Risk: {overall}</span>'
            f"</div>"
        )

    if vulns:
        for v in vulns:
            sev = (v.get("severity") or "low").lower()
            sev_cls = _severity_class(sev)
            rec_name = h(v.get("recommendation") or v.get("rec") or "")
            vuln_text = h(v.get("vulnerability") or v.get("issue") or "")
            mitigation = h(v.get("mitigation") or "")
            content += (
                f'<div class="vuln-card">'
                f'<div class="vuln-title">'
                f'<span class="severity-badge {sev_cls}">{h(sev)}</span>'
                f"{rec_name}"
                f"</div>"
                + (f'<p class="vuln-text">{vuln_text}</p>' if vuln_text else "")
                + (f'<p class="vuln-mitigation">Mitigation: {mitigation}</p>' if mitigation else "")
                + "</div>"
            )
    elif risk_text:
        content += f'<p style="color:#475569;font-size:0.9rem;">{risk_text}</p>'

    if not content:
        return ""

    return _section_wrap("section-risk", "Risk Assessment", content, starts_open=True)


def _build_roadmap(consensus: dict) -> str:
    roadmap = consensus.get("implementation_roadmap") or {}
    p1 = roadmap.get("phase_1_0_3_months") or []
    p2 = roadmap.get("phase_2_3_6_months") or []
    p3 = roadmap.get("phase_3_6_12_months") or []

    if not p1 and not p2 and not p3:
        return ""

    def phase_col(items, title, css_class):
        if isinstance(items, list):
            li_html = "".join(f"<li>{h(item)}</li>" for item in items if item)
        else:
            li_html = f"<li>{h(str(items))}</li>"
        return (
            f'<div class="phase-column">'
            f'<div class="phase-header {css_class}">{h(title)}</div>'
            f'<div class="phase-body"><ul>{li_html}</ul></div>'
            f"</div>"
        )

    content = (
        '<div class="roadmap-grid">'
        + phase_col(p1, "Phase 1 · 0–3 Months", "p1")
        + phase_col(p2, "Phase 2 · 3–6 Months", "p2")
        + phase_col(p3, "Phase 3 · 6–12 Months", "p3")
        + "</div>"
    )

    return _section_wrap("section-roadmap", "Implementation Roadmap", content, starts_open=True)


def _build_pushback(pushback: dict | None) -> str:
    if not pushback:
        return ""
    concern = h(pushback.get("overall_concern") or "")
    objections = pushback.get("pushback") or []

    content = ""
    if concern:
        content += f'<div class="callout-box"><strong>Primary Client Concern:</strong> {concern}</div>'

    for obj in objections:
        rec_title = h(obj.get("recommendation") or obj.get("rec") or "")
        objection = h(obj.get("objection") or obj.get("concern") or "")
        response = h(obj.get("response") or obj.get("answer") or "")
        content += (
            f'<div class="pushback-card">'
            + (f'<div class="pushback-rec">{rec_title}</div>' if rec_title else "")
            + (f'<p class="pushback-objection">Objection: {objection}</p>' if objection else "")
            + (f'<p class="pushback-response">Response: {response}</p>' if response else "")
            + "</div>"
        )

    if not content:
        return ""
    return _section_wrap("section-pushback", "Client Stress Test", content, starts_open=True)


def _build_dissenting(consensus: dict) -> str:
    views = consensus.get("minority_views") or []
    if not views:
        return ""

    cards = []
    for v in views:
        if isinstance(v, dict):
            text = h(v.get("view") or v.get("opinion") or str(v))
            source = h(v.get("source") or v.get("persona") or "")
        else:
            text = h(str(v))
            source = ""
        cards.append(
            f'<div class="quote-card">'
            f'<p class="quote-text">{text}</p>'
            + (f'<div class="quote-source">— {source}</div>' if source else "")
            + "</div>"
        )

    return _section_wrap("section-dissenting", "Dissenting Views", "".join(cards), starts_open=True)


def _build_methodology(
    round1_results: list,
    directions: list | None,
    pushback: dict | None,
    red_team: dict | None,
    case_tags: list | None,
) -> str:
    n_agents = len(round1_results)
    n_directions = len(directions or [])
    has_pushback = bool(pushback)
    has_red_team = bool(red_team)

    bullets = [
        f"<li><strong>{n_agents}</strong> independent consultant agents</li>",
        "<li>3 deliberation rounds: individual analysis → panel review → consensus synthesis</li>",
    ]
    if n_directions:
        bullets.append(f"<li><strong>{n_directions}</strong> competing strategic directions evaluated</li>")
    if has_pushback:
        bullets.append("<li>Client pushback simulation applied and responses integrated</li>")
    if has_red_team:
        bullets.append("<li>Red team adversarial stress test conducted</li>")

    method_html = '<ul class="method-bullets">' + "".join(bullets) + "</ul>"

    # Expertise breakdown
    expertise_counter: Counter = Counter()
    for agent in round1_results:
        persona = agent.get("persona") or {}
        if isinstance(persona, dict):
            for exp in (persona.get("expertise") or []):
                expertise_counter[exp] += 1

    expertise_html = ""
    if expertise_counter:
        chips = "".join(
            f'<span class="expertise-chip">{h(exp)} ({count})</span>'
            for exp, count in expertise_counter.most_common(20)
        )
        expertise_html = (
            "<strong style='font-size:0.82rem;color:#64748b;'>Panel Expertise</strong>"
            f'<div class="expertise-grid" style="margin-top:8px;">{chips}</div>'
        )

    tags_html = ""
    if case_tags:
        tags = "".join(f'<span class="tag-chip">{h(t)}</span>' for t in case_tags)
        tags_html = f"<div style='margin-bottom:12px;'><strong style='font-size:0.82rem;color:#64748b;'>Case Tags</strong><br/>{tags}</div>"

    footnote = '<p class="model-footnote">claude-sonnet-4-6 &middot; ChromaDB &middot; all-MiniLM-L6-v2</p>'

    content = method_html + expertise_html + tags_html + footnote
    return _section_wrap("section-methodology", "Methodology", content, starts_open=False)


# ---------------------------------------------------------------------------
# Sidebar builder
# ---------------------------------------------------------------------------

def _build_sidebar(sections: list[tuple[str, str]], n_recs: int, risk_rating: str) -> str:
    links_html = "".join(
        f'<a href="#{sid}">{h(label)}</a>' for sid, label in sections
    )
    mini = ""
    if n_recs or risk_rating:
        parts = []
        if n_recs:
            parts.append(f"<strong>{n_recs}</strong> recommendations")
        if risk_rating:
            parts.append(f"<strong>{h(risk_rating.upper())}</strong> risk")
        mini = f'<div class="sidebar-mini-stat">{"<br/>".join(parts)}</div>'

    return (
        f'<aside id="sidebar">'
        f"{mini}"
        f"<nav>{links_html}</nav>"
        f"</aside>"
    )


def _build_mobile_nav(sections: list[tuple[str, str]]) -> str:
    links = "".join(
        f'<a href="#{sid}">{h(label)}</a>' for sid, label in sections
    )
    return f'<div id="mobile-nav">{links}</div>'


# ---------------------------------------------------------------------------
# Chart data builder for JS
# ---------------------------------------------------------------------------

def _build_chart_data(consensus: dict, quant_analysis: dict | None) -> dict:
    findings = consensus.get("key_findings") or []
    models = (quant_analysis or {}).get("models") or {}

    conf_labels = []
    conf_values = []
    for f in findings:
        label = str(f.get("finding") or "")
        if len(label) > 35:
            label = label[:34] + "…"
        try:
            val = float(f.get("confidence", 0.7))
        except (TypeError, ValueError):
            val = 0.7
        conf_labels.append(label)
        conf_values.append(val)

    fin_labels = list(models.keys())
    conservative = []
    base = []
    optimistic = []
    for k in fin_labels:
        m = models[k]
        def _f(x):
            try:
                return float(x) if x is not None else None
            except (TypeError, ValueError):
                return None
        conservative.append(_f(m.get("conservative")))
        base.append(_f(m.get("base")))
        optimistic.append(_f(m.get("optimistic")))

    return {
        "confidence": {"labels": conf_labels, "values": conf_values},
        "financial": {
            "labels": fin_labels,
            "conservative": conservative,
            "base": base,
            "optimistic": optimistic,
        },
    }


# ---------------------------------------------------------------------------
# Safe case name (for filename)
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.strip()).strip("_") or "report"


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def build_html_report(
    consensus: dict,
    case_name: str,
    round1_results: list,
    output_dir: Path,
    red_team: dict = None,
    pushback: dict = None,
    quant_analysis: dict = None,
    directions: list = None,
    case_tags: list = None,
    chart_plan: list = None,
) -> "Path | None":
    """
    Generate a self-contained HTML report and write it to output_dir.

    Returns the Path of the written file, or None on failure.
    """
    try:
        # Unwrap if consensus is stored as {"consensus": {...}, "case_name": ...}
        if "consensus" in (consensus or {}) and "executive_summary" not in (consensus or {}):
            consensus = consensus["consensus"]

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        chartjs_source = _get_chartjs()
        chartjs_available = chartjs_source is not None

        today = date.today().strftime("%B %d, %Y")
        safe = _safe_name(case_name)
        out_path = output_dir / f"{safe}_report.html"

        # ── Build sections ────────────────────────────────────────────────
        exec_html = _build_executive_summary(consensus, round1_results, red_team)
        problem_html = _build_problem_statement(consensus)
        findings_html = _build_key_findings(consensus)
        recs_html = _build_recommendations(consensus)
        financial_html = _build_financial(consensus, quant_analysis, chartjs_available)
        risk_html = _build_risk(consensus, red_team)
        roadmap_html = _build_roadmap(consensus)
        pushback_html = _build_pushback(pushback)
        dissenting_html = _build_dissenting(consensus)
        methodology_html = _build_methodology(
            round1_results, directions, pushback, red_team, case_tags
        )

        # ── Sidebar section list (only include sections that rendered) ─────
        _all_sections = [
            ("section-executive", "Executive Summary"),
            ("section-problem", "Problem Statement"),
            ("section-findings", "Key Findings"),
            ("section-recs", "Recommendations"),
            ("section-financial", "Financial Analysis"),
            ("section-risk", "Risk Assessment"),
            ("section-roadmap", "Implementation Roadmap"),
            ("section-pushback", "Client Stress Test"),
            ("section-dissenting", "Dissenting Views"),
            ("section-methodology", "Methodology"),
        ]
        _rendered = {
            "section-executive": bool(exec_html),
            "section-problem": bool(problem_html),
            "section-findings": bool(findings_html),
            "section-recs": bool(recs_html),
            "section-financial": bool(financial_html),
            "section-risk": bool(risk_html),
            "section-roadmap": bool(roadmap_html),
            "section-pushback": bool(pushback_html),
            "section-dissenting": bool(dissenting_html),
            "section-methodology": bool(methodology_html),
        }
        visible_sections = [(sid, label) for sid, label in _all_sections if _rendered[sid]]

        n_recs = len(consensus.get("recommendations") or [])
        risk_rating_str = (red_team or {}).get("overall_risk_rating") or ""
        sidebar_html = _build_sidebar(visible_sections, n_recs, risk_rating_str)
        mobile_nav_html = _build_mobile_nav(visible_sections)

        # ── Inject planned charts into sections ───────────────────────────
        if chart_plan:
            chart_blocks = _build_chart_blocks(chart_plan)
            section_vars = {
                "section-executive": "exec_html",
                "section-problem": "problem_html",
                "section-findings": "findings_html",
                "section-recs": "recs_html",
                "section-financial": "financial_html",
                "section-risk": "risk_html",
                "section-roadmap": "roadmap_html",
            }
            section_html_map = {
                "section-executive": exec_html,
                "section-problem": problem_html,
                "section-findings": findings_html,
                "section-recs": recs_html,
                "section-financial": financial_html,
                "section-risk": risk_html,
                "section-roadmap": roadmap_html,
            }
            for sid, charts_html in chart_blocks.items():
                if sid in section_html_map:
                    section_html_map[sid] = _inject_charts_into_section(
                        section_html_map[sid], charts_html
                    )
            exec_html = section_html_map["section-executive"]
            problem_html = section_html_map["section-problem"]
            findings_html = section_html_map["section-findings"]
            recs_html = section_html_map["section-recs"]
            financial_html = section_html_map["section-financial"]
            risk_html = section_html_map["section-risk"]
            roadmap_html = section_html_map["section-roadmap"]

        # ── Chart data JSON ───────────────────────────────────────────────
        chart_data = _build_chart_data(consensus, quant_analysis)
        report_data_json = json.dumps(chart_data, ensure_ascii=False)
        chart_specs_json = json.dumps(chart_plan or [], ensure_ascii=False)

        # ── JS assembly ───────────────────────────────────────────────────
        js_code = (
            _JS_TEMPLATE
            .replace("__REPORT_DATA__", report_data_json)
            .replace("__CHART_SPECS__", chart_specs_json)
        )
        if chartjs_source:
            js_block = (
                f"<script>{chartjs_source}</script>\n"
                f"<script>{js_code}</script>"
            )
        else:
            js_block = f"<script>{js_code}</script>"

        # ── Assemble body sections ────────────────────────────────────────
        body_sections = "".join(filter(None, [
            exec_html,
            problem_html,
            findings_html,
            recs_html,
            financial_html,
            risk_html,
            roadmap_html,
            pushback_html,
            dissenting_html,
            methodology_html,
        ]))

        # ── Full HTML ─────────────────────────────────────────────────────
        html_doc = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="UTF-8"/>\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n'
            f"<title>{h(case_name)} — Consulting Report</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n"
            "<body>\n"
            # Navbar
            '<nav id="top-navbar">\n'
            f'  <div class="nav-title">{h(case_name)}</div>\n'
            f'  <span class="nav-meta">{h(today)}</span>\n'
            '  <button class="btn-export" id="btn-export-pdf">&#8862; Export PDF</button>\n'
            "</nav>\n"
            # Mobile nav
            f"{mobile_nav_html}\n"
            # Layout
            '<div id="layout">\n'
            f"{sidebar_html}\n"
            '<main id="main-content">\n'
            f"{body_sections}\n"
            "</main>\n"
            "</div>\n"
            f"{js_block}\n"
            "</body>\n"
            "</html>\n"
        )

        out_path.write_text(html_doc, encoding="utf-8")
        logger.info("HTML report written to %s", out_path)
        return out_path

    except Exception as exc:
        logger.error("HTML report generation failed: %s", exc, exc_info=True)
        return None
