"""
chart_planner.py — Makes a Sonnet call to plan visualizations for the HTML report.

Called after consensus is built, before the HTML report is rendered. Returns a list
of chart spec dicts that html_reporter.py uses to inject Chart.js visuals.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a data visualization consultant at McKinsey. You have \
a case analysis with financial data and strategic recommendations. \
Your job is to determine which charts and visual elements will \
make the strongest possible case to the reader.

For each chart you recommend, specify:
{
  "id": "unique_id",
  "chart_type": "bar|line|doughnut|horizontal_bar|waterfall|comparison|timeline|funnel|stat_callout",
  "title": "insight-driven title, not just a label (e.g. 'Revenue declined 23% while costs held steady' not 'Revenue and Costs')",
  "data": { "labels": [...], "values": [...] },
  "placement": "section-executive|section-problem|section-findings|section-recs|section-financial|section-risk|section-roadmap",
  "story": "one sentence explaining what this chart proves and why it matters",
  "design_notes": "any specific styling — highlight a bar in red, add a trend line, annotate a key data point"
}

For stat_callout type use: "data": { "value": "65%", "caption": "short label" }

For comparison/grouped charts use: "data": { "labels": [...], "datasets": [{"label": "Before", "values": [...]}, {"label": "After", "values": [...]}] }

For waterfall charts use: "data": { "labels": ["Baseline", "Rec 1", "Rec 2", "Projected"], "values": [base_val, delta1, delta2, final_val] } where values[0] is the starting bar and subsequent values are positive/negative increments.

Rules:
- Every chart must make an argument, not just display data. If a chart doesn't change how the reader thinks about the problem, cut it.
- Use comparison charts (grouped bar, before/after) when showing the gap between current state and recommended state.
- Use line charts for trends over time. Annotate the inflection points.
- Use doughnut charts for composition (where does revenue come from, how is the budget allocated). Never for more than 5 segments.
- Use horizontal bar charts for rankings (top recommendations by impact, risk severity comparison).
- Use large stat callouts (not charts) for single dramatic numbers like '65% of employees run out of money between paychecks.'
- Create a waterfall chart showing how recommendations combine to change the financial picture (current deficit → rec 1 impact → rec 2 impact → rec 3 impact → projected surplus).
- Aim for 5-8 charts total. More than that dilutes impact.
- Every recommendation section should have at least one visual — either a chart showing the projected impact or a before/after comparison.
- If the case data doesn't support a specific chart, don't fake it. Use a stat callout or qualitative visual instead.

Respond ONLY with a JSON array of chart specifications. No markdown fences, no extra text."""


def plan_charts(
    case_brief: str,
    financial_data: str,
    consensus: dict,
    market_context: str = "",
) -> list:
    """
    Call Sonnet to determine what visualizations should appear in the HTML report.

    Returns a list of chart spec dicts (may be empty if the call fails).
    Each spec has: id, chart_type, title, data, placement, story, design_notes.
    """
    try:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv()

        brief_snippet = (case_brief or "")[:3000]
        fin_snippet = (financial_data or "No structured financial data available.")[:1500]
        consensus_snippet = json.dumps(consensus, ensure_ascii=False, indent=2)[:3500]
        market_snippet = (market_context or "No market research available.")[:1500]

        user_content = (
            f"## Case Brief\n{brief_snippet}\n\n"
            f"## Market Research Data\n{market_snippet}\n\n"
            f"## Financial Data\n{fin_snippet}\n\n"
            f"## Consensus Analysis\n{consensus_snippet}\n\n"
            "IMPORTANT: Prioritize charts that use the market research data — "
            "benchmark comparisons (client vs industry average), market sizing "
            "(client share vs total addressable market), and trend data. "
            "If market research found a benchmark (e.g. industry average $520/member/year "
            "vs client at $476), that gap IS a chart. If a growth rate was found, "
            "that IS a line chart. Market data exists to be shown, not just mentioned in text."
        )

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        text = response.content[0].text.strip()

        # Strip markdown fences if the model wrapped the JSON anyway
        if text.startswith("```"):
            parts = text.split("```", 2)
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()

        specs = json.loads(text)
        if not isinstance(specs, list):
            logger.warning("Chart planner returned a non-list response; ignoring.")
            return []

        # Basic validation — drop specs missing required fields
        valid = []
        for s in specs:
            if not isinstance(s, dict):
                continue
            if not s.get("id") or not s.get("chart_type"):
                continue
            valid.append(s)

        logger.info("Chart planner produced %d valid specifications.", len(valid))
        return valid

    except Exception as exc:
        logger.warning("Chart planning failed (%s); proceeding without chart plan.", exc)
        return []


def extract_financial_text(case_data: dict) -> str:
    """
    Pull spreadsheet / financial text out of case_data['files'] for the chart planner.
    Falls back to the case brief if no spreadsheets were found.
    """
    files = case_data.get("files") or []
    parts = []
    for f in files:
        text = f.get("text") or ""
        # Spreadsheets tend to have short lines of numbers
        if any(ext in str(f.get("filename") or "").lower() for ext in (".xlsx", ".xls", ".csv")):
            parts.append(text[:1500])
        elif "table" in str(f.get("filename") or "").lower():
            parts.append(text[:800])
    return "\n\n".join(parts) if parts else ""
