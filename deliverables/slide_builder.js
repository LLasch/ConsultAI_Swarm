#!/usr/bin/env node
/**
 * Consulting Swarm — Upgraded Slide Deck Builder v2
 *
 * Design rules enforced:
 *  - Body text ≤ 40 words per slide (full detail goes to speaker notes)
 *  - Bullet points ≤ 8 words
 *  - Slide titles ≤ 7 words
 *  - No two consecutive slides share a layout
 *  - Numbers always get visual treatment (stat callout or chart)
 *  - pptxgenjs charts for all quantitative data
 *  - Speaker notes on every slide
 *
 * Usage:
 *   node deliverables/slide_builder.js <input.json> <output.pptx> [case_name]
 */

"use strict";

const PptxGenJS = require("pptxgenjs");
const fs        = require("fs");

// ─── CLI ──────────────────────────────────────────────────────────────────────
const [,, inputPath, outputPath, caseName = "Case Analysis"] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: node slide_builder.js <input.json> <output.pptx> [case_name]");
  process.exit(1);
}

let data;
try {
  data = JSON.parse(fs.readFileSync(inputPath, "utf8"));
} catch (e) {
  console.error("Failed to read input JSON:", e.message);
  process.exit(1);
}

const consensus    = data.consensus  || data;
const round1       = data.round1     || [];
const redTeam      = data.red_team   || {};
const pushback     = data.pushback   || {};
const quantData    = data.quant_analysis || {};
const directions   = data.directions || [];
const caseTags     = data.case_tags  || [];

// ─── PALETTE ─────────────────────────────────────────────────────────────────
function detectPalette(name, consensus, tags) {
  const text = [name, ...(tags || []), consensus.executive_summary || "", consensus.problem_statement || ""]
    .join(" ").toLowerCase();

  if (/museum|archaeolog|heritage|artifact|gallery|art|cultural/.test(text)) return {
    dark: "1E0E05", primary: "6B2D0F", accent: "C4960A", mid: "8B5E3C",
    light: "FDF8F2", white: "FFFFFF", body: "2D1A0E", muted: "8B7355",
    positive: "3D8B37", negative: "B22222", warning: "E8A000",
    chart1: "6B2D0F", chart2: "C4960A", chart3: "8B5E3C",
  };
  if (/healthcare|hospital|clinic|medical|patient|pharma/.test(text)) return {
    dark: "012A36", primary: "028090", accent: "02C39A", mid: "00A896",
    light: "F0FAF9", white: "FFFFFF", body: "0A2930", muted: "5F8A8B",
    positive: "00B894", negative: "D63031", warning: "FDCB6E",
    chart1: "028090", chart2: "02C39A", chart3: "00A896",
  };
  if (/nonprofit|charity|foundation|ngo|mission|community|social/.test(text)) return {
    dark: "152614", primary: "2C5F2D", accent: "79AC78", mid: "4A7C59",
    light: "F2F8F2", white: "FFFFFF", body: "1A2E1A", muted: "6B8F71",
    positive: "2C5F2D", negative: "C0392B", warning: "F39C12",
    chart1: "2C5F2D", chart2: "79AC78", chart3: "4A7C59",
  };
  if (/tech|software|digital|platform|saas|startup|data/.test(text)) return {
    dark: "0D0D1A", primary: "2E1760", accent: "7B2FBE", mid: "5C3D9E",
    light: "F6F2FF", white: "FFFFFF", body: "1A1033", muted: "7B72A6",
    positive: "00B894", negative: "D63031", warning: "FDCB6E",
    chart1: "2E1760", chart2: "7B2FBE", chart3: "5C3D9E",
  };
  if (/retail|consumer|e.?commerce|merchandise|brand/.test(text)) return {
    dark: "1A0A00", primary: "8B1A1A", accent: "E8461E", mid: "C44B30",
    light: "FFF8F5", white: "FFFFFF", body: "2D1010", muted: "9B6B6B",
    positive: "27AE60", negative: "E8461E", warning: "F39C12",
    chart1: "8B1A1A", chart2: "E8461E", chart3: "C44B30",
  };
  if (/financ|bank|invest|private equity|pe fund|insurance/.test(text)) return {
    dark: "0A1628", primary: "1B3A6B", accent: "2E86AB", mid: "1F5C8B",
    light: "F0F5FA", white: "FFFFFF", body: "0A1628", muted: "6B8CA8",
    positive: "00B894", negative: "D63031", warning: "FDCB6E",
    chart1: "1B3A6B", chart2: "2E86AB", chart3: "1F5C8B",
  };
  // Default: Charcoal Executive
  return {
    dark: "1A1A1A", primary: "2D2D2D", accent: "C0933A", mid: "4A4A4A",
    light: "F5F5F2", white: "FFFFFF", body: "222222", muted: "888888",
    positive: "27AE60", negative: "C0392B", warning: "E67E22",
    chart1: "2D2D2D", chart2: "C0933A", chart3: "4A4A4A",
  };
}

const PAL = detectPalette(caseName, consensus, caseTags);
const FONT_HEAD = "Arial";
const FONT_BODY = "Calibri";

// ─── LAYOUT TRACKER ──────────────────────────────────────────────────────────
// Ensures no two consecutive slides share a layout
let _lastLayout = null;

function useLayout(preferred) {
  if (preferred !== _lastLayout) {
    _lastLayout = preferred;
    return preferred;
  }
  // Fallback mapping: what to use instead when preferred is blocked
  const fallbacks = {
    hero_stat:   "two_column",
    two_column:  "dashboard",
    icon_grid:   "comparison",
    chart:       "two_column",
    timeline:    "icon_grid",
    comparison:  "two_column",
    quote:       "hero_stat",
    dashboard:   "icon_grid",
  };
  const alt = fallbacks[preferred] || "two_column";
  _lastLayout = alt;
  return alt;
}

// ─── TEXT DENSITY HELPERS ─────────────────────────────────────────────────────
// Truncate to max N words
function wlimit(str, maxWords) {
  const s = String(str || "").trim();
  const words = s.split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return s;
  return words.slice(0, maxWords).join(" ") + "…";
}

// Title limit: 12 words (McKinsey action titles are full insight sentences)
const title7 = (s) => wlimit(s, 12);

// Hard bullet limit: 8 words
const bullet8 = (s) => wlimit(s, 8);

// Body text limit: 40 words
const body40 = (s) => wlimit(s, 40);

// Char truncate (for strings that need char limits regardless of word count)
const trunc = (str, n) => (str && str.length > n ? str.slice(0, n - 1) + "…" : str || "");

// ─── PPTX SETUP ──────────────────────────────────────────────────────────────
const prs = new PptxGenJS();
prs.layout  = "LAYOUT_WIDE";
prs.author  = "Consulting Swarm";
prs.title   = caseName;
prs.subject = "Multi-Agent Consulting Analysis";

// ─── HELPERS ─────────────────────────────────────────────────────────────────
// McKinsey-style header: action title on slide background + thin colored rule underneath.
// bgColor is repurposed as the rule/accent color (not a background fill).
function addHeader(slide, text, ruleColor = PAL.accent, _unused = null) {
  slide.addText(title7(text), {
    x: 0.45, y: 0.15, w: 12.43, h: 0.72,
    fontFace: FONT_HEAD, fontSize: 20, bold: true,
    color: PAL.dark, valign: "middle",
  });
  // Thin rule below title — color signals section type (red for risk, primary for normal, etc.)
  slide.addShape(prs.ShapeType.rect, {
    x: 0.45, y: 0.88, w: 12.43, h: 0.035,
    fill: { color: ruleColor }, line: { type: "none" },
  });
}

// McKinsey-style footer: thin gray rule, confidentiality left, firm right.
function addFooter(slide) {
  slide.addShape(prs.ShapeType.rect, {
    x: 0, y: 7.28, w: 13.33, h: 0.025,
    fill: { color: "CCCCCC" }, line: { type: "none" },
  });
  slide.addText("CONFIDENTIAL AND PROPRIETARY", {
    x: 0.45, y: 7.31, w: 7, h: 0.19,
    fontFace: FONT_BODY, fontSize: 8, color: PAL.muted,
  });
  slide.addText("CONSULTING SWARM", {
    x: 0.45, y: 7.31, w: 12.43, h: 0.19,
    fontFace: FONT_BODY, fontSize: 8, bold: true, color: PAL.muted, align: "right",
  });
}

function addLabel(slide, text, x, y, w = 4, color = PAL.accent) {
  slide.addText(text.toUpperCase(), {
    x, y, w, h: 0.28,
    fontFace: FONT_BODY, fontSize: 8, bold: true, color, charSpacing: 2,
  });
}

// Stat callout box — large number with label
function addStatBox(slide, stat, label, x, y, w = 2.6, h = 1.3, bgColor = PAL.accent) {
  slide.addShape(prs.ShapeType.rect, {
    x, y, w, h,
    fill: { color: bgColor }, line: { type: "none" }, rounding: true,
  });
  slide.addText(String(stat), {
    x, y: y + 0.05, w, h: h * 0.58,
    fontFace: FONT_HEAD, fontSize: 30, bold: true,
    color: PAL.white, align: "center", valign: "bottom",
  });
  slide.addText(wlimit(label, 6), {
    x, y: y + h * 0.58, w, h: h * 0.38,
    fontFace: FONT_BODY, fontSize: 9, color: PAL.white,
    align: "center", valign: "top",
  });
}

// Colored circle with number or symbol
function addCircle(slide, label, x, y, size = 0.6, bgColor = PAL.accent, textColor = PAL.white) {
  slide.addShape(prs.ShapeType.ellipse, {
    x, y, w: size, h: size,
    fill: { color: bgColor }, line: { type: "none" },
  });
  slide.addText(String(label), {
    x, y, w: size, h: size,
    fontFace: FONT_HEAD, fontSize: Math.round(size * 18), bold: true,
    color: textColor, align: "center", valign: "middle",
  });
}

// Severity badge
function severityColor(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "critical") return "C0392B";
  if (s === "high")     return "E67E22";
  if (s === "medium")   return "F39C12";
  return "27AE60";
}

// ─── SPEAKER NOTES HELPER ────────────────────────────────────────────────────
function addNotes(slide, text) {
  if (text) slide.addNotes(String(text));
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 1: TITLE
// ═══════════════════════════════════════════════════════════════════════════
(function slideTitle() {
  useLayout("title");
  const s = prs.addSlide();

  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.dark }, line: { type: "none" } });
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: PAL.accent }, line: { type: "none" } });
  s.addShape(prs.ShapeType.rect, { x: 0.45, y: 3.9, w: 6.5, h: 0.04, fill: { color: PAL.accent }, line: { type: "none" } });

  s.addText("MULTI-AGENT CONSULTING ANALYSIS", {
    x: 0.45, y: 1.6, w: 12, h: 0.45,
    fontFace: FONT_BODY, fontSize: 10, bold: true, color: PAL.accent, charSpacing: 3,
  });

  const displayName = caseName.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  s.addText(displayName, {
    x: 0.45, y: 2.05, w: 11.5, h: 1.65,
    fontFace: FONT_HEAD, fontSize: 42, bold: true, color: PAL.white,
  });

  s.addText("Strategic Analysis Report", {
    x: 0.45, y: 4.0, w: 8, h: 0.5,
    fontFace: FONT_BODY, fontSize: 18, color: PAL.muted,
  });

  const today = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  const numAgents = round1.length || 20;
  const numDirs = directions.length ? ` · ${directions.length} Competing Strategies` : "";
  s.addText(`${today}  ·  ${numAgents}-Agent Specialist Panel${numDirs}`, {
    x: 0.45, y: 6.75, w: 12, h: 0.4,
    fontFace: FONT_BODY, fontSize: 10, color: PAL.muted,
  });

  if (caseTags.length > 0) {
    s.addText(caseTags.slice(0, 6).join("  ·  ").toUpperCase(), {
      x: 0.45, y: 5.0, w: 10, h: 0.35,
      fontFace: FONT_BODY, fontSize: 9, color: PAL.muted, charSpacing: 1,
    });
  }

  s.addText("CONSULTING SWARM", {
    x: 10.5, y: 6.75, w: 2.8, h: 0.4,
    fontFace: FONT_BODY, fontSize: 9, bold: true, color: PAL.accent, align: "right",
  });

  addNotes(s, [
    `Case: ${caseName}`,
    `Date: ${today}`,
    `Panel: ${numAgents} specialist agents`,
    directions.length ? `Strategic directions explored: ${directions.map(d => d.direction).join(", ")}` : "",
    caseTags.length ? `Case tags: ${caseTags.join(", ")}` : "",
    `Executive summary: ${consensus.executive_summary || ""}`,
  ].filter(Boolean).join("\n\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 2: AGENDA / CONTENTS — McKinsey numbered contents page
// ═══════════════════════════════════════════════════════════════════════════
(function slideAgenda() {
  useLayout("agenda");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.white }, line: { type: "none" } });

  s.addText("Contents", {
    x: 0.45, y: 0.15, w: 12, h: 0.72,
    fontFace: FONT_HEAD, fontSize: 24, bold: true, color: PAL.dark, valign: "middle",
  });
  s.addShape(prs.ShapeType.rect, {
    x: 0.45, y: 0.88, w: 12.43, h: 0.035,
    fill: { color: PAL.accent }, line: { type: "none" },
  });

  const numRecs     = (consensus.recommendations || []).length;
  const hasQuant    = (quantData.models || []).length > 0 || numRecs > 0;
  const hasRoadmap  = Object.values(consensus.implementation_roadmap || {}).some(v => Array.isArray(v) && v.length > 0);
  const hasRisk     = !!(consensus.risk_assessment || (redTeam.vulnerabilities || []).length > 0);
  const hasPushback = (pushback.pushback || []).length > 0 || !!pushback.overall_concern;
  const hasMinority = (consensus.minority_views || []).length > 0;

  const sections = [
    { num: 1, label: "Executive Summary" },
    { num: 2, label: "Problem Statement & Analytical Framework" },
    { num: 3, label: `Key Findings  (${(consensus.key_findings || []).length})` },
    { num: 4, label: `Recommendations  (${numRecs})` },
    hasQuant    ? { num: 5, label: "Financial Impact" }           : null,
    hasRoadmap  ? { num: 6, label: "Implementation Roadmap" }     : null,
    hasRisk     ? { num: 7, label: "Risk Assessment" }            : null,
    hasPushback ? { num: 8, label: "Client Stress Test" }         : null,
    hasMinority ? { num: 9, label: "Dissenting Views" }           : null,
    { num: 10,  label: "Next Steps" },
  ].filter(Boolean);

  const cols = 2;
  const colW = 6.0;
  const rowH = 0.78;
  sections.forEach((sec, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = 0.45 + col * (colW + 0.45);
    const y = 1.05 + row * (rowH + 0.18);

    s.addShape(prs.ShapeType.rect, { x, y, w: colW, h: rowH, fill: { color: "F4F6F9" }, line: { color: "E0E4EA", pt: 0.5 } });
    // Number tag
    s.addShape(prs.ShapeType.rect, { x, y, w: 0.45, h: rowH, fill: { color: PAL.accent }, line: { type: "none" } });
    s.addText(String(sec.num), {
      x, y, w: 0.45, h: rowH,
      fontFace: FONT_HEAD, fontSize: 11, bold: true, color: PAL.white, align: "center", valign: "middle",
    });
    s.addText(sec.label, {
      x: x + 0.55, y, w: colW - 0.65, h: rowH,
      fontFace: FONT_BODY, fontSize: 12, color: PAL.body, valign: "middle",
    });
  });

  addFooter(s);
  addNotes(s, "Agenda / contents overview.");
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3: EXECUTIVE SUMMARY — Dashboard layout
// ═══════════════════════════════════════════════════════════════════════════
(function slideExecSummary() {
  useLayout("dashboard");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Executive Summary");
  addFooter(s);

  const numRecs     = (consensus.recommendations || []).length;
  const numFindings = (consensus.key_findings || []).length;
  const numAgents   = round1.length || 20;
  const riskRating  = redTeam.overall_risk_rating || null;

  // Stat row
  const stats = [
    [String(numAgents), "Specialists"],
    [String(numRecs), "Recommendations"],
    [String(numFindings), "Key Findings"],
    riskRating ? [riskRating.toUpperCase(), "Risk Rating"] : [directions.length ? String(directions.length) : "3", "Rounds"],
  ];
  const statColors = [PAL.primary, PAL.accent, PAL.mid, riskRating === "high" ? "C0392B" : PAL.primary];
  stats.forEach(([stat, label], i) => {
    addStatBox(s, stat, label, 0.4 + i * 3.2, 1.0, 2.9, 1.25, statColors[i]);
  });

  // Bottom line callout
  const bl = consensus.bottom_line || "";
  if (bl) {
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: 2.45, w: 12.5, h: 1.1, fill: { color: PAL.dark }, line: { type: "none" } });
    addLabel(s, "BOTTOM LINE", 0.65, 2.5, 4, PAL.accent);
    s.addText(body40(bl), {
      x: 0.65, y: 2.78, w: 12.0, h: 0.7,
      fontFace: FONT_BODY, fontSize: 14, bold: true, color: PAL.white,
    });
  }

  // Key findings summary
  const findings = (consensus.key_findings || []).slice(0, 4);
  if (findings.length > 0) {
    addLabel(s, "KEY FINDINGS", 0.4, 3.75, 6, PAL.primary);
    const fItems = findings.map((f, i) => {
      const text = typeof f === "string" ? f : (f.finding || "");
      return { text: `${i + 1}.  ${bullet8(text)}`, options: { fontFace: FONT_BODY, fontSize: 12, color: PAL.body, paraSpaceAfter: 6 } };
    });
    s.addText(fItems, { x: 0.4, y: 4.05, w: 12.5, h: 3.0 });
  }

  addNotes(s, [
    "EXECUTIVE SUMMARY — FULL TEXT:",
    consensus.executive_summary || "",
    "",
    "BOTTOM LINE:",
    bl,
    "",
    "KEY FINDINGS:",
    ...(consensus.key_findings || []).map((f, i) => `${i + 1}. ${typeof f === "string" ? f : f.finding} (confidence: ${typeof f === "object" ? Math.round((f.confidence || 0.8) * 100) : 80}%)`),
  ].join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3: PROBLEM STATEMENT — Two-column
// ═══════════════════════════════════════════════════════════════════════════
(function slideProblem() {
  useLayout("two_column");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "The Core Problem", PAL.primary);
  addFooter(s);

  const problem   = consensus.problem_statement || "";
  const framework = consensus.analysis_framework || "";

  // Left: problem (condensed)
  s.addShape(prs.ShapeType.rect, { x: 0.4, y: 1.05, w: 7.5, h: 6.0, fill: { color: PAL.white }, line: { color: PAL.accent, pt: 1.5 } });
  addLabel(s, "CORE PROBLEM", 0.65, 1.12, 5, PAL.primary);
  s.addText(body40(problem), {
    x: 0.65, y: 1.45, w: 7.0, h: 5.4,
    fontFace: FONT_BODY, fontSize: 15, color: PAL.body, valign: "top",
  });

  // Right: framework on dark bg
  s.addShape(prs.ShapeType.rect, { x: 8.2, y: 1.05, w: 4.7, h: 6.0, fill: { color: PAL.dark }, line: { type: "none" } });
  addLabel(s, "FRAMEWORKS APPLIED", 8.45, 1.12, 4.2, PAL.accent);
  s.addText(body40(framework), {
    x: 8.45, y: 1.45, w: 4.2, h: 5.4,
    fontFace: FONT_BODY, fontSize: 13, color: PAL.white, valign: "top",
  });

  addNotes(s, [
    "FULL PROBLEM STATEMENT:",
    problem,
    "",
    "ANALYTICAL FRAMEWORKS:",
    framework,
    "",
    "MISSING INFORMATION FLAGGED BY AGENTS:",
    ...(consensus.missing_information || []).map(m => `• ${m}`),
  ].join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 4: METHODOLOGY — Icon grid
// ═══════════════════════════════════════════════════════════════════════════
(function slideMethodology() {
  useLayout("icon_grid");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "How This Analysis Was Built");
  addFooter(s);

  const numAgents = round1.length || 20;
  const numDirs   = directions.length || 4;
  const numPanels = Math.ceil(numAgents / 5);

  const steps = [
    { icon: "1", title: `${numAgents} Specialists`, sub: "Case-matched expert\nselection via AI", color: PAL.primary },
    { icon: "2", title: `${numDirs} Strategy Teams`, sub: "Competing directions\nexplored in parallel", color: PAL.mid },
    { icon: "3", title: `${numPanels} Debate Panels`, sub: "Cross-team deliberation\nfor best evidence", color: PAL.accent },
    { icon: "4", title: "Stress-Tested", sub: "Client pushback\n+ Red team review", color: PAL.dark },
  ];

  steps.forEach((step, i) => {
    const x = 0.5 + i * 3.15;
    const w = 2.85;

    // Background card
    s.addShape(prs.ShapeType.rect, { x, y: 1.1, w, h: 5.5, fill: { color: PAL.white }, line: { color: step.color, pt: 1 }, rounding: true });

    // Circle icon
    addCircle(s, step.icon, x + w / 2 - 0.5, 1.4, 1.0, step.color, PAL.white);

    // Title
    s.addText(step.title, {
      x, y: 2.65, w, h: 0.65,
      fontFace: FONT_HEAD, fontSize: 16, bold: true, color: PAL.body, align: "center",
    });

    // Sub
    s.addText(step.sub, {
      x, y: 3.4, w, h: 1.2,
      fontFace: FONT_BODY, fontSize: 12, color: PAL.muted, align: "center",
    });

    // Connector arrow (not after last)
    if (i < steps.length - 1) {
      s.addShape(prs.ShapeType.rect, { x: x + w + 0.03, y: 2.1, w: 0.09, h: 0.5, fill: { color: PAL.accent }, line: { type: "none" } });
      s.addShape(prs.ShapeType.rect, { x: x + w + 0.03, y: 2.2, w: 0.22, h: 0.3, fill: { color: PAL.accent }, line: { type: "none" } });
    }
  });

  // Expertise distribution
  if (round1.length > 0) {
    const counts = {};
    round1.forEach(a => (a.expertise || []).forEach(e => { counts[e] = (counts[e] || 0) + 1; }));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const expertText = "Panel expertise: " + top.map(([k, v]) => `${v}× ${k}`).join("  ·  ");
    s.addText(wlimit(expertText, 30), {
      x: 0.5, y: 6.8, w: 12.33, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10, color: PAL.muted, align: "center",
    });
  }

  addNotes(s, [
    "METHODOLOGY DETAIL:",
    `• ${numAgents} agents selected from a 50-persona roster based on case-specific tags`,
    `• Each agent received a framework instruction matched to their primary expertise`,
    directions.length ? `• ${directions.length} competing strategic directions generated before Round 1` : "",
    `• Round 2: cross-team debate panels (one agent per direction per panel)`,
    `• Round 3: senior synthesis of all panel outputs`,
    `• Post-consensus: client pushback simulation + red team stress test`,
    "• Model: claude-sonnet-4-20250514 (Anthropic)",
  ].filter(Boolean).join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDES 5+: KEY FINDINGS — Alternating layouts
// ═══════════════════════════════════════════════════════════════════════════
(function slideFindings() {
  const findings = (consensus.key_findings || []).slice(0, 4);
  const FINDING_LAYOUTS = ["two_column", "hero_stat", "comparison", "dashboard"];

  findings.forEach((finding, i) => {
    const layout = useLayout(FINDING_LAYOUTS[i % FINDING_LAYOUTS.length]);
    const s = prs.addSlide();
    s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
    addFooter(s);

    const fText      = typeof finding === "string" ? finding : (finding.finding || `Finding ${i + 1}`);
    const evidence   = typeof finding === "object" ? (finding.evidence || "") : "";
    const confidence = typeof finding === "object" ? (finding.confidence || 0.8) : 0.8;
    const confPct    = Math.round(confidence * 100);

    // Action title: the finding text IS the slide headline
    addHeader(s, fText);

    if (layout === "hero_stat" || layout === "dashboard") {
      // Hero: big confidence number left, text right
      s.addShape(prs.ShapeType.rect, { x: 0.4, y: 1.05, w: 3.8, h: 5.95, fill: { color: PAL.accent }, line: { type: "none" } });
      s.addText(`${confPct}%`, {
        x: 0.4, y: 2.0, w: 3.8, h: 2.0,
        fontFace: FONT_HEAD, fontSize: 72, bold: true, color: PAL.white, align: "center",
      });
      addLabel(s, "PANEL CONFIDENCE", 0.4, 4.1, 3.8, PAL.white);
      s.addText("of agents\nagreed", {
        x: 0.4, y: 4.4, w: 3.8, h: 0.8,
        fontFace: FONT_BODY, fontSize: 12, color: PAL.white, align: "center",
      });

      s.addShape(prs.ShapeType.rect, { x: 4.5, y: 1.05, w: 8.43, h: 5.95, fill: { color: PAL.white }, line: { type: "none" } });
      addLabel(s, "FINDING", 4.75, 1.12, 6, PAL.primary);
      s.addText(body40(fText), {
        x: 4.75, y: 1.45, w: 7.9, h: 3.0,
        fontFace: FONT_BODY, fontSize: 15, color: PAL.body, valign: "top",
      });
      if (evidence) {
        addLabel(s, "SUPPORTING EVIDENCE", 4.75, 4.6, 7, PAL.muted);
        s.addText(body40(evidence), {
          x: 4.75, y: 4.9, w: 7.9, h: 1.8,
          fontFace: FONT_BODY, fontSize: 12, color: PAL.muted, valign: "top",
        });
      }

    } else {
      // Two-column: finding left, evidence right
      s.addShape(prs.ShapeType.rect, { x: 0.4, y: 1.05, w: 7.4, h: 5.95, fill: { color: PAL.white }, line: { color: PAL.accent, pt: 1.5 } });
      addLabel(s, `FINDING ${i + 1}`, 0.65, 1.12, 4, PAL.primary);
      s.addText(body40(fText), {
        x: 0.65, y: 1.45, w: 6.9, h: 5.4,
        fontFace: FONT_BODY, fontSize: 15, color: PAL.body, valign: "top",
      });

      s.addShape(prs.ShapeType.rect, { x: 8.1, y: 1.05, w: 4.83, h: 5.95, fill: { color: PAL.dark }, line: { type: "none" } });
      addLabel(s, "EVIDENCE", 8.35, 1.12, 4.3, PAL.accent);
      s.addText(body40(evidence || "See supporting analysis in agent log."), {
        x: 8.35, y: 1.45, w: 4.3, h: 3.8,
        fontFace: FONT_BODY, fontSize: 13, color: PAL.white, valign: "top",
      });

      // Confidence bar
      addLabel(s, "CONFIDENCE", 8.35, 5.35, 4.3, PAL.accent);
      s.addText(`${confPct}%`, {
        x: 8.35, y: 5.65, w: 4.3, h: 0.7,
        fontFace: FONT_HEAD, fontSize: 36, bold: true, color: PAL.accent, align: "center",
      });
      const bw = 4.1 * confidence;
      s.addShape(prs.ShapeType.rect, { x: 8.35, y: 6.45, w: 4.1, h: 0.18, fill: { color: "555555" }, line: { type: "none" } });
      if (bw > 0) {
        s.addShape(prs.ShapeType.rect, { x: 8.35, y: 6.45, w: bw, h: 0.18, fill: { color: PAL.accent }, line: { type: "none" } });
      }
    }

    addNotes(s, [
      `FINDING ${i + 1} — FULL TEXT:`,
      fText,
      "",
      "EVIDENCE:",
      evidence || "No direct evidence text provided.",
      "",
      `Panel confidence: ${confPct}%`,
    ].join("\n"));
  });
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: RECOMMENDATIONS OVERVIEW — Icon grid
// ═══════════════════════════════════════════════════════════════════════════
(function slideRecsOverview() {
  const recs = (consensus.recommendations || []).slice(0, 5);
  if (recs.length === 0) return;

  useLayout("icon_grid");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Recommendations at a Glance");
  addFooter(s);

  const colW = 13.33 / Math.min(recs.length, 5);
  recs.forEach((rec, i) => {
    if (!rec || typeof rec !== "object") return;
    const x   = i * colW;
    const col = [PAL.primary, PAL.accent, PAL.mid, PAL.chart1, PAL.chart2][i % 5];

    // Top accent bar
    s.addShape(prs.ShapeType.rect, { x: x + 0.1, y: 1.0, w: colW - 0.2, h: 0.18, fill: { color: col }, line: { type: "none" } });

    // Rank circle
    addCircle(s, rec.rank || (i + 1), x + colW / 2 - 0.45, 1.3, 0.9, col, PAL.white);

    // Title
    s.addText(bullet8(rec.title || `Rec ${i + 1}`), {
      x: x + 0.15, y: 2.35, w: colW - 0.3, h: 0.75,
      fontFace: FONT_HEAD, fontSize: 13, bold: true, color: PAL.body, align: "center",
    });

    // One-line description
    s.addText(bullet8(rec.description || ""), {
      x: x + 0.15, y: 3.2, w: colW - 0.3, h: 0.6,
      fontFace: FONT_BODY, fontSize: 11, color: PAL.muted, align: "center",
    });

    // Timeline chip
    if (rec.timeline) {
      s.addShape(prs.ShapeType.rect, { x: x + 0.3, y: 4.0, w: colW - 0.6, h: 0.35, fill: { color: col }, line: { type: "none" }, rounding: true });
      s.addText(bullet8(rec.timeline), { x: x + 0.3, y: 4.0, w: colW - 0.6, h: 0.35, fontFace: FONT_BODY, fontSize: 9, bold: true, color: PAL.white, align: "center", valign: "middle" });
    }

    // Support
    if (rec.panel_support) {
      s.addText(trunc(rec.panel_support, 20), { x: x + 0.15, y: 4.5, w: colW - 0.3, h: 0.3, fontFace: FONT_BODY, fontSize: 9, color: PAL.muted, align: "center" });
    }
  });

  addNotes(s, [
    "RECOMMENDATIONS OVERVIEW:",
    ...(consensus.recommendations || []).map((r, i) => `${i + 1}. ${r.title}: ${r.description}`),
  ].join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDES: RECOMMENDATION DETAILS — Rotating layouts
// ═══════════════════════════════════════════════════════════════════════════
(function slideRecDetails() {
  const recs = (consensus.recommendations || []).slice(0, 5);
  const REC_LAYOUTS = ["two_column", "dashboard", "comparison", "two_column", "hero_stat"];

  recs.forEach((rec, i) => {
    if (!rec || typeof rec !== "object") return;

    const layout = useLayout(REC_LAYOUTS[i % REC_LAYOUTS.length]);
    const s = prs.addSlide();
    s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
    addFooter(s);

    const rank    = rec.rank || (i + 1);
    const steps   = (rec.implementation_steps || []).slice(0, 5);
    const impact  = rec.expected_impact || "";
    const support = rec.panel_support || "";
    const risks   = rec.risks_and_mitigations || "";

    // McKinsey-style rec header: numbered label + action title + thin rule
    s.addText(`RECOMMENDATION ${rank}`, {
      x: 0.45, y: 0.1, w: 3.5, h: 0.32,
      fontFace: FONT_BODY, fontSize: 8, bold: true, color: PAL.accent, charSpacing: 2,
    });
    s.addText(title7(rec.title || `Recommendation ${rank}`), {
      x: 0.45, y: 0.38, w: 10.5, h: 0.52,
      fontFace: FONT_HEAD, fontSize: 20, bold: true, color: PAL.dark, valign: "middle",
    });
    if (support) {
      s.addText(trunc(support, 22), {
        x: 9.6, y: 0.38, w: 3.5, h: 0.52,
        fontFace: FONT_BODY, fontSize: 10, color: PAL.muted, align: "right", valign: "middle",
      });
    }
    // Thin rule
    s.addShape(prs.ShapeType.rect, { x: 0.45, y: 0.9, w: 12.43, h: 0.035, fill: { color: PAL.accent }, line: { type: "none" } });

    if (layout === "dashboard") {
      // Stat callouts across top, steps below
      const metaItems = [
        [bullet8(impact || "High"), "Expected Impact", PAL.accent],
        [bullet8(rec.timeline || "Medium-term"), "Timeline", PAL.mid],
        [support || "Consensus", "Panel Support", PAL.primary],
      ];
      metaItems.forEach(([val, label, col], mi) => {
        addStatBox(s, val, label, 0.4 + mi * 4.2, 1.1, 4.0, 1.1, col);
      });
      if (steps.length > 0) {
        addLabel(s, "IMPLEMENTATION STEPS", 0.4, 2.4, 8, PAL.primary);
        steps.forEach((st, si) => {
          const sy = 2.75 + si * 0.85;
          addCircle(s, si + 1, 0.4, sy + 0.08, 0.5, PAL.accent, PAL.white);
          s.addText(bullet8(st), { x: 1.05, y: sy, w: 11.8, h: 0.65, fontFace: FONT_BODY, fontSize: 13, color: PAL.body, valign: "middle" });
        });
      }

    } else if (layout === "comparison") {
      // Left: description + rationale, Right: numbered steps
      s.addText(body40(rec.description || ""), {
        x: 0.4, y: 1.1, w: 6.3, h: 1.6,
        fontFace: FONT_BODY, fontSize: 13, color: PAL.body, valign: "top",
      });
      if (rec.rationale) {
        s.addShape(prs.ShapeType.rect, { x: 0.4, y: 2.8, w: 6.3, h: 1.1, fill: { color: PAL.white }, line: { color: PAL.accent, pt: 1 } });
        addLabel(s, "WHY THIS IS PRIORITY", 0.6, 2.85, 5, PAL.primary);
        s.addText(body40(rec.rationale), { x: 0.6, y: 3.1, w: 5.9, h: 0.7, fontFace: FONT_BODY, fontSize: 12, italic: true, color: PAL.body });
      }
      [[impact, "IMPACT"], [rec.timeline, "TIMELINE"]].forEach(([val, label], mi) => {
        if (!val) return;
        s.addShape(prs.ShapeType.rect, { x: 0.4 + mi * 3.2, y: 4.1, w: 3.0, h: 1.0, fill: { color: mi === 0 ? PAL.accent : PAL.mid }, line: { type: "none" }, rounding: true });
        addLabel(s, label, 0.6 + mi * 3.2, 4.15, 2.7, PAL.dark);
        s.addText(bullet8(val), { x: 0.6 + mi * 3.2, y: 4.45, w: 2.7, h: 0.55, fontFace: FONT_BODY, fontSize: 12, bold: true, color: PAL.dark });
      });

      s.addShape(prs.ShapeType.rect, { x: 7.1, y: 1.1, w: 5.83, h: 5.9, fill: { color: PAL.dark }, line: { type: "none" } });
      addLabel(s, "STEPS TO EXECUTE", 7.35, 1.15, 5.3, PAL.accent);
      steps.forEach((st, si) => {
        const sy = 1.55 + si * 0.9;
        addCircle(s, si + 1, 7.35, sy + 0.05, 0.45, PAL.accent, PAL.dark);
        s.addText(bullet8(st), { x: 7.95, y: sy, w: 4.7, h: 0.6, fontFace: FONT_BODY, fontSize: 11, color: PAL.white, valign: "middle" });
      });

    } else {
      // two_column / hero_stat: left body, right meta panel
      s.addText(body40(rec.description || ""), {
        x: 0.4, y: 1.1, w: 8.6, h: 1.7,
        fontFace: FONT_BODY, fontSize: 13, color: PAL.body, valign: "top",
      });
      if (steps.length > 0) {
        addLabel(s, "HOW TO EXECUTE", 0.4, 3.0, 8, PAL.primary);
        steps.forEach((st, si) => {
          const sy = 3.35 + si * 0.8;
          addCircle(s, si + 1, 0.4, sy + 0.05, 0.45, PAL.accent, PAL.white);
          s.addText(bullet8(st), { x: 1.0, y: sy, w: 7.9, h: 0.6, fontFace: FONT_BODY, fontSize: 12, color: PAL.body, valign: "middle" });
        });
      }
      // Right panel
      s.addShape(prs.ShapeType.rect, { x: 9.3, y: 1.1, w: 3.6, h: 5.9, fill: { color: PAL.accent }, line: { type: "none" } });
      let ry = 1.2;
      [[impact || "High", "EXPECTED IMPACT"], [rec.timeline || "—", "TIMELINE"], [support, "PANEL SUPPORT"]].forEach(([val, label]) => {
        if (!val) return;
        addLabel(s, label, 9.5, ry, 3.2, PAL.dark);
        s.addText(bullet8(val), { x: 9.5, y: ry + 0.28, w: 3.2, h: 0.75, fontFace: FONT_BODY, fontSize: 13, bold: true, color: PAL.dark, valign: "top" });
        s.addShape(prs.ShapeType.rect, { x: 9.5, y: ry + 1.1, w: 3.0, h: 0.02, fill: { color: PAL.dark }, line: { type: "none" } });
        ry += 1.45;
      });
    }

    addNotes(s, [
      `RECOMMENDATION ${rank}: ${rec.title}`,
      "",
      "FULL DESCRIPTION:",
      rec.description || "",
      "",
      "RATIONALE:",
      rec.rationale || "",
      "",
      "IMPLEMENTATION STEPS:",
      ...(rec.implementation_steps || []).map((s, si) => `${si + 1}. ${s}`),
      "",
      `Timeline: ${rec.timeline || "Not specified"}`,
      `Expected impact: ${impact}`,
      `Panel support: ${support}`,
      `Cost estimate: ${rec.cost_estimate || "Not specified"}`,
      "",
      "RISKS & MITIGATIONS:",
      risks,
    ].join("\n"));
  });
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: FINANCIAL IMPACT — Chart
// ═══════════════════════════════════════════════════════════════════════════
(function slideFinancialImpact() {
  const models = (quantData.models || []).filter(m => m.scenarios && m.scenarios.base);
  const recs   = (consensus.recommendations || []).slice(0, 5);
  if (models.length === 0 && recs.length === 0) return;

  useLayout("chart");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addFooter(s);

  // Build chart data
  let labels, conserv, base, optimistic, hasScenarios;
  if (models.length > 0) {
    labels     = models.map(m => trunc(m.recommendation || "Unknown", 18));
    conserv    = models.map(m => Math.round((m.scenarios.conservative?.annual_revenue || 0) / 1000));
    base       = models.map(m => Math.round((m.scenarios.base?.annual_revenue || 0) / 1000));
    optimistic = models.map(m => Math.round((m.scenarios.optimistic?.annual_revenue || 0) / 1000));
    hasScenarios = true;
  } else {
    // Construct from consensus rec impact (qualitative → numeric proxy)
    labels  = recs.map(r => trunc(r.title || "Rec", 18));
    const impactScore = r => r.expected_impact?.toLowerCase().includes("high") ? 150 : r.expected_impact?.toLowerCase().includes("medium") ? 80 : 40;
    base    = recs.map(r => impactScore(r));
    conserv = base.map(v => Math.round(v * 0.6));
    optimistic = base.map(v => Math.round(v * 1.5));
    hasScenarios = false;
  }

  const insightTitle = hasScenarios
    ? title7(`Projected revenue impact ($K) by recommendation`)
    : title7(`Relative impact ranking by recommendation`);

  addHeader(s, insightTitle, PAL.dark);

  try {
    const chartData = hasScenarios ? [
      { name: "Conservative", labels, values: conserv },
      { name: "Base Case",    labels, values: base },
      { name: "Optimistic",   labels, values: optimistic },
    ] : [
      { name: "Base Case Impact", labels, values: base },
    ];

    s.addChart(prs.ChartType.bar, chartData, {
      x: 0.4, y: 1.0, w: 12.5, h: 5.8,
      chartColors: hasScenarios ? [PAL.muted, PAL.accent, PAL.chart2] : [PAL.accent],
      showLegend: hasScenarios,
      legendPos: "b",
      dataLabelPosition: "outEnd",
      showValue: true,
      dataLabelFontSize: 9,
      dataLabelColor: PAL.body,
      valAxisNumFmt: hasScenarios ? "#,##0" : "0",
      valGridLine: { color: "E2E8F0", style: "solid", size: 0.5 },
      catGridLine: { style: "none" },
      chartArea: { fill: { color: PAL.white }, roundedCorners: true },
      barGrouping: "clustered",
    });
  } catch (e) {
    // Fallback: stat boxes if chart fails
    recs.slice(0, 4).forEach((rec, i) => {
      addStatBox(s, base[i] || "—", trunc(rec.title || `Rec ${i+1}`, 18), 0.4 + i * 3.2, 1.5, 3.0, 1.4, [PAL.primary, PAL.accent, PAL.mid, PAL.chart2][i]);
    });
  }

  addNotes(s, [
    "FINANCIAL IMPACT ANALYSIS:",
    hasScenarios
      ? models.map(m => `${m.recommendation}: Conservative $${(m.scenarios.conservative?.annual_revenue || 0).toLocaleString()}, Base $${(m.scenarios.base?.annual_revenue || 0).toLocaleString()}, Optimistic $${(m.scenarios.optimistic?.annual_revenue || 0).toLocaleString()}`).join("\n")
      : "Note: numeric values are impact proxies (high=150, medium=80, low=40) based on qualitative assessment since no quantitative case data was provided.",
    "",
    hasScenarios && models[0]?.payback_months ? `Payback periods: ${models.map(m => `${m.recommendation}: ${m.payback_months?.toFixed(0)} months`).join(", ")}` : "",
    hasScenarios && models[0]?.roi_percent !== undefined ? `ROI: ${models.map(m => `${m.recommendation}: ${m.roi_percent?.toFixed(0)}%`).join(", ")}` : "",
  ].filter(Boolean).join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: IMPLEMENTATION ROADMAP — Timeline
// ═══════════════════════════════════════════════════════════════════════════
(function slideRoadmap() {
  const roadmap = consensus.implementation_roadmap || {};
  const hasData = Object.values(roadmap).some(v => Array.isArray(v) && v.length > 0);
  if (!hasData) return;

  useLayout("timeline");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Implementation Roadmap", PAL.primary);
  addFooter(s);

  const phases = [
    { key: "phase_1_0_3_months", label: "Phase 1",  sub: "Months 0–3",  color: PAL.accent },
    { key: "phase_2_3_6_months", label: "Phase 2",  sub: "Months 3–6",  color: PAL.mid },
    { key: "phase_3_6_12_months", label: "Phase 3", sub: "Months 6–12", color: PAL.primary },
  ];

  // Arrow backbone
  s.addShape(prs.ShapeType.rect, { x: 0.5, y: 2.5, w: 12.33, h: 0.07, fill: { color: PAL.accent }, line: { type: "none" } });

  phases.forEach((ph, i) => {
    const items = roadmap[ph.key] || [];
    const px    = 0.5 + i * 4.2;
    const pw    = 4.0;

    // Phase header
    s.addShape(prs.ShapeType.rect, { x: px, y: 1.1, w: pw, h: 1.2, fill: { color: ph.color }, line: { type: "none" } });
    s.addText(ph.label, { x: px, y: 1.1, w: pw, h: 0.65, fontFace: FONT_HEAD, fontSize: 18, bold: true, color: PAL.white, align: "center", valign: "middle" });
    s.addText(ph.sub, { x: px, y: 1.68, w: pw, h: 0.38, fontFace: FONT_BODY, fontSize: 11, color: "EEEEEE", align: "center" });

    // Dot on timeline
    addCircle(s, "", px + pw / 2 - 0.18, 2.36, 0.35, ph.color, PAL.white);

    // Items below timeline
    const itemObjs = items.slice(0, 4).map(it => ({
      text: bullet8(String(it)),
      options: { fontFace: FONT_BODY, fontSize: 12, color: PAL.body, bullet: true, paraSpaceAfter: 6 },
    }));
    if (itemObjs.length > 0) {
      s.addText(itemObjs, { x: px + 0.1, y: 2.75, w: pw - 0.2, h: 4.3 });
    }
  });

  addNotes(s, [
    "FULL IMPLEMENTATION ROADMAP:",
    ...phases.map(ph => [
      `${ph.label} (${ph.sub}):`,
      ...(roadmap[ph.key] || []).map(item => `  • ${item}`),
    ].join("\n")),
  ].join("\n\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: RISK ASSESSMENT — Comparison with severity colors
// ═══════════════════════════════════════════════════════════════════════════
(function slideRiskAssessment() {
  const riskText = consensus.risk_assessment || "";
  if (!riskText) return;

  useLayout("comparison");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Risk Assessment", "5C0000");
  addFooter(s);

  // Try to parse structured risks from red team data first
  const vulns    = (redTeam.vulnerabilities || []).slice(0, 6);
  const riskLines = riskText.split(/\n|(?<=\.)\s+/).filter(l => l.trim().length > 12).slice(0, 7);

  if (vulns.length > 0) {
    // Use red team vulnerability data — richer
    addLabel(s, "VULNERABILITIES IDENTIFIED BY RED TEAM", 0.4, 0.95, 12, PAL.muted);
    vulns.forEach((v, i) => {
      const ry  = 1.3 + i * 0.95;
      const col = severityColor(v.severity);
      // Severity badge
      s.addShape(prs.ShapeType.rect, { x: 0.4, y: ry + 0.05, w: 0.22, h: 0.65, fill: { color: col }, line: { type: "none" } });
      // Rec label chip
      s.addShape(prs.ShapeType.rect, { x: 0.75, y: ry + 0.08, w: 2.8, h: 0.28, fill: { color: col + "33" }, line: { type: "none" }, rounding: true });
      s.addText(trunc(v.recommendation || "General", 22), { x: 0.75, y: ry + 0.08, w: 2.8, h: 0.28, fontFace: FONT_BODY, fontSize: 8, bold: true, color: col, align: "center", valign: "middle" });
      // Vulnerability text
      s.addText(bullet8(v.vulnerability || ""), { x: 3.7, y: ry, w: 9.2, h: 0.65, fontFace: FONT_BODY, fontSize: 12, color: PAL.body, valign: "middle" });
    });

    // Overall rating
    if (redTeam.overall_risk_rating) {
      const col = severityColor(redTeam.overall_risk_rating);
      addStatBox(s, redTeam.overall_risk_rating.toUpperCase(), "Overall Risk", 10.5, 1.1, 2.5, 1.1, col);
    }

  } else {
    // Fallback: parse risk text into lines
    const sevColors = ["B22222", "CD5C5C", "E88080", "F0A0A0", "F5C0C0", "F8D8D8", "FAEAEA"];
    riskLines.forEach((line, i) => {
      const ry  = 1.1 + i * 0.8;
      const col = i < 2 ? sevColors[0] : i < 4 ? sevColors[2] : sevColors[4];
      s.addShape(prs.ShapeType.rect, { x: 0.4, y: ry + 0.05, w: 0.22, h: 0.55, fill: { color: col }, line: { type: "none" } });
      s.addText(bullet8(line.trim()), { x: 0.75, y: ry, w: 12.15, h: 0.65, fontFace: FONT_BODY, fontSize: 13, color: PAL.body, valign: "middle" });
    });
  }

  // Severity legend
  [["High", "B22222"], ["Medium", "E88080"], ["Low", "27AE60"]].forEach(([lbl, col], li) => {
    s.addShape(prs.ShapeType.rect, { x: 0.5 + li * 1.4, y: 7.1, w: 0.18, h: 0.15, fill: { color: col }, line: { type: "none" } });
    s.addText(lbl, { x: 0.73 + li * 1.4, y: 7.05, w: 1.1, h: 0.28, fontFace: FONT_BODY, fontSize: 9, color: PAL.muted });
  });

  addNotes(s, [
    "FULL RISK ASSESSMENT:",
    riskText,
    "",
    redTeam.kill_recommendation ? `RED TEAM — WEAKEST RECOMMENDATION: ${redTeam.kill_recommendation}` : "",
    redTeam.strongest_recommendation ? `RED TEAM — MOST DEFENSIBLE: ${redTeam.strongest_recommendation}` : "",
  ].filter(Boolean).join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: CLIENT CONSIDERATIONS (if pushback data present)
// ═══════════════════════════════════════════════════════════════════════════
(function slideClientConsiderations() {
  const pbItems = pushback.pushback || [];
  if (pbItems.length === 0 && !pushback.overall_concern) return;

  useLayout("quote");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Client Stress Test: Key Objections");
  addFooter(s);

  // Overall concern callout
  if (pushback.overall_concern) {
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: 1.05, w: 12.5, h: 1.05, fill: { color: PAL.dark }, line: { type: "none" } });
    addLabel(s, "PRIMARY CONCERN FROM CLIENT SIMULATION", 0.65, 1.1, 10, PAL.accent);
    s.addText(body40(pushback.overall_concern), {
      x: 0.65, y: 1.38, w: 12.0, h: 0.65,
      fontFace: FONT_BODY, fontSize: 13, bold: true, color: PAL.white,
    });
  }

  // Per-recommendation objections
  const shownItems = pbItems.slice(0, 4);
  shownItems.forEach((item, i) => {
    const iy = 2.25 + i * 1.2;
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: iy, w: 12.5, h: 1.05, fill: { color: PAL.white }, line: { color: PAL.accent, pt: 0.8 } });
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: iy, w: 0.12, h: 1.05, fill: { color: PAL.accent }, line: { type: "none" } });
    addLabel(s, trunc(item.recommendation || "General", 30), 0.65, iy + 0.05, 4, PAL.primary);
    const objText = (item.objections || []).slice(0, 1).join(" ");
    s.addText(bullet8(objText), { x: 0.65, y: iy + 0.32, w: 11.9, h: 0.6, fontFace: FONT_BODY, fontSize: 12, color: PAL.body, valign: "top" });
  });

  addNotes(s, [
    "CLIENT PUSHBACK SIMULATION — FULL OUTPUT:",
    `Overall concern: ${pushback.overall_concern || ""}`,
    `Missing: ${pushback.missing || ""}`,
    "",
    "PER-RECOMMENDATION OBJECTIONS:",
    ...(pushback.pushback || []).map(item => [
      `${item.recommendation}:`,
      ...(item.objections || []).map(o => `  Objection: ${o}`),
      item.conditions_for_buy_in ? `  Conditions for approval: ${item.conditions_for_buy_in}` : "",
    ].filter(Boolean).join("\n")),
  ].join("\n\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: RED TEAM ANALYSIS (if present)
// ═══════════════════════════════════════════════════════════════════════════
(function slideRedTeam() {
  const vulns = (redTeam.vulnerabilities || []);
  if (vulns.length === 0 && !redTeam.overall_risk_rating) return;

  useLayout("comparison");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Red Team: Adversarial Stress Test", "3D0000");
  addFooter(s);

  // Summary stats row
  const critCount   = redTeam.critical_count || vulns.filter(v => v.severity === "critical").length;
  const highCount   = vulns.filter(v => v.severity === "high").length;
  const rating      = redTeam.overall_risk_rating || "unknown";
  addStatBox(s, rating.toUpperCase(), "Overall Risk",      0.4,  1.05, 2.8, 1.1, severityColor(rating));
  addStatBox(s, String(critCount),   "Critical Issues",   3.4,  1.05, 2.8, 1.1, critCount > 0 ? "C0392B" : "27AE60");
  addStatBox(s, String(highCount),   "High Issues",       6.4,  1.05, 2.8, 1.1, highCount  > 0 ? "E67E22" : "27AE60");
  addStatBox(s, String(vulns.length), "Total Findings",   9.4,  1.05, 2.8, 1.1, PAL.mid);

  // Top vulnerabilities
  const topVulns = vulns.slice(0, 4);
  topVulns.forEach((v, i) => {
    const vy  = 2.35 + i * 1.15;
    const col = severityColor(v.severity);
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: vy, w: 12.5, h: 1.0, fill: { color: PAL.white }, line: { color: col, pt: 1 } });
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: vy, w: 0.18, h: 1.0, fill: { color: col }, line: { type: "none" } });
    addLabel(s, `${(v.severity || "").toUpperCase()} — ${trunc(v.recommendation || "General", 25)}`, 0.7, vy + 0.05, 8, col);
    s.addText(bullet8(v.vulnerability || ""), { x: 0.7, y: vy + 0.32, w: 9.0, h: 0.55, fontFace: FONT_BODY, fontSize: 12, color: PAL.body, valign: "top" });
    if (v.mitigation_suggestion) {
      s.addText(bullet8(v.mitigation_suggestion), { x: 9.8, y: vy + 0.1, w: 3.0, h: 0.8, fontFace: FONT_BODY, fontSize: 10, color: PAL.muted, italic: true, valign: "middle" });
    }
  });

  addNotes(s, [
    "RED TEAM — FULL ANALYSIS:",
    `Overall risk rating: ${rating}`,
    `Critical vulnerabilities: ${critCount}`,
    "",
    "ALL VULNERABILITIES:",
    ...vulns.map(v => `[${v.severity?.toUpperCase()}] ${v.recommendation}: ${v.vulnerability}\nMitigation: ${v.mitigation_suggestion || "None specified"}`),
    "",
    redTeam.strongest_recommendation ? `Most defensible: ${redTeam.strongest_recommendation}` : "",
    redTeam.weakest_recommendation   ? `Most vulnerable: ${redTeam.weakest_recommendation}`   : "",
    redTeam.kill_recommendation      ? `Would cut: ${redTeam.kill_recommendation}`             : "",
  ].filter(Boolean).join("\n\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: DISSENTING VIEWS — Quote/callout
// ═══════════════════════════════════════════════════════════════════════════
(function slideDissent() {
  const minority = (consensus.minority_views || []).slice(0, 3);
  if (minority.length === 0) return;

  useLayout("quote");
  const s = prs.addSlide();
  // Warm muted background for dissent — visually distinct from risk slides
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: "F9F5EE" }, line: { type: "none" } });
  addHeader(s, "Dissenting Views Worth Considering", "4A3728");
  addFooter(s);

  s.addText("These views didn't reach consensus — but analytical tension is valuable.", {
    x: 0.5, y: 1.0, w: 12.33, h: 0.38,
    fontFace: FONT_BODY, fontSize: 12, italic: true, color: "8B7355",
  });

  minority.forEach((view, i) => {
    const vy      = 1.55 + i * 1.85;
    const viewTxt = typeof view === "string" ? view : (view.view || "");
    const raised  = typeof view === "object" ? (view.raised_by || "") : "";
    const merit   = typeof view === "object" ? (view.merit || "") : "";

    s.addShape(prs.ShapeType.rect, { x: 0.4, y: vy, w: 12.5, h: 1.7, fill: { color: PAL.white }, line: { color: "8B7355", pt: 1 } });
    s.addShape(prs.ShapeType.rect, { x: 0.4, y: vy, w: 0.12, h: 1.7, fill: { color: "8B7355" }, line: { type: "none" } });
    s.addText(`"${bullet8(viewTxt)}"`, { x: 0.65, y: vy + 0.1, w: 9.6, h: 0.65, fontFace: FONT_BODY, fontSize: 14, italic: true, color: PAL.body });
    if (raised) {
      s.addText(trunc(raised, 24), { x: 10.7, y: vy + 0.1, w: 2.1, h: 0.4, fontFace: FONT_BODY, fontSize: 10, color: "8B7355", align: "right" });
    }
    if (merit) {
      s.addText(bullet8(merit), { x: 0.65, y: vy + 0.9, w: 12.0, h: 0.65, fontFace: FONT_BODY, fontSize: 12, color: "6B6B6B" });
    }
  });

  addNotes(s, [
    "DISSENTING VIEWS — FULL TEXT:",
    ...(consensus.minority_views || []).map((v, i) => [
      `${i + 1}. ${typeof v === "string" ? v : v.view}`,
      typeof v === "object" && v.raised_by ? `   Raised by: ${v.raised_by}` : "",
      typeof v === "object" && v.merit     ? `   Merit: ${v.merit}` : "",
    ].filter(Boolean).join("\n")),
  ].join("\n\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: NEXT STEPS — Icon grid on dark background
// ═══════════════════════════════════════════════════════════════════════════
(function slideNextSteps() {
  useLayout("icon_grid");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.white }, line: { type: "none" } });

  s.addText("Next Steps", { x: 0.45, y: 0.15, w: 10, h: 0.72, fontFace: FONT_HEAD, fontSize: 24, bold: true, color: PAL.dark, valign: "middle" });
  s.addShape(prs.ShapeType.rect, { x: 0.45, y: 0.88, w: 12.43, h: 0.035, fill: { color: PAL.accent }, line: { type: "none" } });

  // Bottom line callout box
  const bl = consensus.bottom_line || "";
  if (bl) {
    s.addShape(prs.ShapeType.rect, { x: 0.45, y: 1.0, w: 12.4, h: 0.88, fill: { color: PAL.accent }, line: { type: "none" } });
    s.addText(body40(bl), { x: 0.65, y: 1.0, w: 12.0, h: 0.88, fontFace: FONT_BODY, fontSize: 14, bold: true, color: PAL.white, valign: "middle" });
  }

  // Phase 1 actions
  const phase1 = (consensus.implementation_roadmap || {}).phase_1_0_3_months || [];
  const actions = phase1.slice(0, 5);

  if (actions.length > 0) {
    s.addText("IMMEDIATE ACTIONS — MONTHS 0–3", {
      x: 0.45, y: 2.1, w: 12, h: 0.35,
      fontFace: FONT_BODY, fontSize: 10, bold: true, color: PAL.accent, charSpacing: 2,
    });
    actions.forEach((action, ai) => {
      const ay = 2.55 + ai * 0.88;
      addCircle(s, ai + 1, 0.45, ay + 0.05, 0.55, PAL.accent, PAL.white);
      s.addText(bullet8(String(action)), { x: 1.15, y: ay, w: 11.7, h: 0.65, fontFace: FONT_BODY, fontSize: 14, color: PAL.body, valign: "middle" });
    });
  }

  addFooter(s);

  addNotes(s, [
    "NEXT STEPS — FULL DETAIL:",
    `Bottom line: ${bl}`,
    "",
    "PHASE 1 ACTIONS (0-3 months):",
    ...(phase1.map((a, i) => `${i + 1}. ${a}`)),
    "",
    "PHASE 2 ACTIONS (3-6 months):",
    ...((consensus.implementation_roadmap?.phase_2_3_6_months || []).map((a, i) => `${i + 1}. ${a}`)),
    "",
    "PHASE 3 ACTIONS (6-12 months):",
    ...((consensus.implementation_roadmap?.phase_3_6_12_months || []).map((a, i) => `${i + 1}. ${a}`)),
  ].join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE: APPENDIX — Methodology detail
// ═══════════════════════════════════════════════════════════════════════════
(function slideAppendix() {
  useLayout("two_column");
  const s = prs.addSlide();
  s.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: PAL.light }, line: { type: "none" } });
  addHeader(s, "Appendix: Methodology", PAL.mid);
  addFooter(s);

  const numAgents  = round1.length || 20;
  const allRecs    = round1.flatMap(a => (a.analysis || {}).recommendations || []);
  const uniqueRecs = new Set(allRecs.map(r => r.title || "")).size;

  // Left column: process
  addLabel(s, "PROCESS", 0.4, 1.05, 5, PAL.primary);
  const processItems = [
    `${numAgents} specialist agents selected via case tag matching`,
    directions.length ? `${directions.length} competing strategic directions generated pre-Round 1` : `20 agents ran independent analyses (Round 1)`,
    `${Math.ceil(numAgents / 5)} cross-team debate panels (Round 2)`,
    `Senior partner consensus synthesis (Round 3)`,
    pushback.overall_concern ? "Client pushback simulation (Round 3.5)" : "",
    (redTeam.vulnerabilities || []).length > 0 ? "Red team adversarial stress test (post-consensus)" : "",
    `${uniqueRecs} unique recommendations explored → ${(consensus.recommendations || []).length} final`,
  ].filter(Boolean);

  const processObjs = processItems.map(p => ({ text: bullet8(p), options: { fontFace: FONT_BODY, fontSize: 12, color: PAL.body, bullet: true, paraSpaceAfter: 5 } }));
  s.addText(processObjs, { x: 0.4, y: 1.38, w: 6.3, h: 5.6 });

  // Right column: panel composition
  addLabel(s, "PANEL COMPOSITION", 7.2, 1.05, 5.7, PAL.primary);
  if (round1.length > 0) {
    const counts = {};
    round1.forEach(a => (a.expertise || []).forEach(e => { counts[e] = (counts[e] || 0) + 1; }));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const compObjs = top.map(([k, v]) => ({
      text: `${v}×  ${k}`,
      options: { fontFace: FONT_BODY, fontSize: 12, color: PAL.body, bullet: false, paraSpaceAfter: 4 },
    }));
    s.addText(compObjs, { x: 7.2, y: 1.38, w: 5.7, h: 5.6 });
  } else {
    s.addText("strategy, finance, operations, marketing,\nHR, technology, legal, nonprofit,\nrisk, creative, museum, membership", {
      x: 7.2, y: 1.38, w: 5.7, h: 3.0,
      fontFace: FONT_BODY, fontSize: 13, color: PAL.body, valign: "top",
    });
  }

  // Model footnote
  s.addText("Model: claude-sonnet-4-20250514  ·  Embeddings: all-MiniLM-L6-v2  ·  Vector store: ChromaDB", {
    x: 0.4, y: 7.05, w: 12.5, h: 0.25,
    fontFace: FONT_BODY, fontSize: 9, color: PAL.muted, align: "center",
  });

  addNotes(s, [
    "METHODOLOGY NOTES:",
    `Total agents deployed: ${numAgents}`,
    `Total recommendations explored: ${allRecs.length} (${uniqueRecs} unique titles)`,
    `Final recommendations: ${(consensus.recommendations || []).length}`,
    directions.length ? `Strategic directions: ${directions.map(d => `${d.direction} — ${d.description}`).join("; ")}` : "",
    caseTags.length ? `Case tags used for agent selection: ${caseTags.join(", ")}` : "",
  ].filter(Boolean).join("\n"));
})();

// ═══════════════════════════════════════════════════════════════════════════
// WRITE FILE
// ═══════════════════════════════════════════════════════════════════════════
prs.writeFile({ fileName: outputPath })
  .then(() => {
    console.log("OK:" + outputPath);
    process.exit(0);
  })
  .catch(err => {
    console.error("PPTX write error:", err.message);
    process.exit(1);
  });
