"""
Quantitative modeling step between Round 1 and Round 2.
One Sonnet call to extract financial assumptions, then pure Python math.
Cost: ~$0.01
"""

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ASSUMPTION_PROMPT = """Here are consultant recommendations from a business case analysis. Extract every quantifiable financial claim or assumption made.

Return ONLY this JSON array (no markdown fences):
[
  {{
    "recommendation": "recommendation title",
    "assumptions": [
      {{
        "variable": "descriptive variable name",
        "value": 300,
        "unit": "customers/year",
        "basis": "agent's stated reasoning or your estimate"
      }}
    ],
    "revenue_estimate_annual": 150000,
    "cost_estimate_total": 45000,
    "timeline_months": 12
  }}
]

If agents didn't give specific numbers, estimate reasonable ranges based on context and set a "estimated": true flag in the assumption. Include all recommendations that have any financial dimension.

Recommendations:
{recommendations_text}

Case context:
{case_brief_excerpt}"""


def run_quantitative_analysis(
    case_brief: str,
    round1_results: list,
    output_dir: Path = Path("output"),
) -> dict:
    """
    Extract quantitative assumptions and run financial models.
    Returns financial analysis dict injected into Round 2 context.
    """
    # Collect and deduplicate recommendations
    seen_titles: set = set()
    unique_recs = []
    for agent in round1_results:
        for rec in agent.get("analysis", {}).get("recommendations", [])[:3]:
            title = rec.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_recs.append({
                    "title": rec.get("title", ""),
                    "description": rec.get("description", ""),
                    "confidence": rec.get("confidence", 0.7),
                    "impact": rec.get("impact", ""),
                })

    if not unique_recs:
        return {"error": "No recommendations to model", "models": [], "summary": ""}

    assumptions = _extract_assumptions(json.dumps(unique_recs[:15], indent=2), case_brief[:2000])
    models = _run_financial_models(assumptions)

    result = {
        "assumptions": assumptions,
        "models": models,
        "summary": _build_summary(models),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "quant_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


def _extract_assumptions(recommendations_text: str, case_brief_excerpt: str) -> list:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": ASSUMPTION_PROMPT.format(
                    recommendations_text=recommendations_text,
                    case_brief_excerpt=case_brief_excerpt,
                ),
            }],
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return json.loads(text)
    except Exception as e:
        logger.warning(f"Quantitative assumption extraction failed: {e}")
        return []


def _run_financial_models(assumptions: list) -> list:
    models = []
    for item in assumptions:
        if not isinstance(item, dict):
            continue
        revenue = float(item.get("revenue_estimate_annual", 0) or 0)
        cost = float(item.get("cost_estimate_total", 0) or 0)
        months = int(item.get("timeline_months", 12) or 12)

        net_annual = revenue - (cost / max(months / 12, 1))
        payback = _payback(cost, net_annual / 12) if net_annual > 0 and cost > 0 else None
        roi = round((revenue - cost) / cost * 100, 1) if cost > 0 else None
        npv = _npv(revenue, cost)

        flags = []
        if revenue > 0 and cost > revenue * 3:
            flags.append("Cost appears high relative to revenue")
        if revenue > 500_000 and not item.get("assumptions"):
            flags.append("Large revenue projection lacks supporting assumptions")

        models.append({
            "recommendation": item.get("recommendation", "Unknown"),
            "revenue_estimate_annual": revenue,
            "cost_estimate_total": cost,
            "timeline_months": months,
            "scenarios": {
                "conservative": _scenario(revenue, cost, 0.6),
                "base": _scenario(revenue, cost, 1.0),
                "optimistic": _scenario(revenue, cost, 1.5),
            },
            "payback_months": payback,
            "roi_percent": roi,
            "npv_3yr": round(npv, 0),
            "flags": flags,
        })
    return models


def _scenario(revenue: float, cost: float, mult: float) -> dict:
    r = revenue * mult
    return {"annual_revenue": round(r, 0), "net_contribution": round(r - cost, 0), "profitable": r > cost}


def _payback(total_cost: float, monthly_net: float):
    if monthly_net <= 0 or total_cost <= 0:
        return None
    return round(total_cost / monthly_net, 1)


def _npv(annual_revenue: float, total_cost: float, rate: float = 0.08, years: int = 3) -> float:
    pv = sum(annual_revenue / (1 + rate) ** t for t in range(1, years + 1))
    return pv - total_cost


def _build_summary(models: list) -> str:
    if not models:
        return "No quantitative models generated."
    parts = []
    for m in models:
        revenue = m.get("revenue_estimate_annual", 0)
        roi = m.get("roi_percent")
        payback = m.get("payback_months")
        flags = m.get("flags", [])
        line = f"**{m['recommendation']}**: "
        if revenue:
            line += f"~${revenue:,.0f}/yr revenue"
        if roi is not None:
            line += f", {roi:.0f}% ROI"
        if payback:
            line += f", {payback:.0f}mo payback"
        if flags:
            line += f" ⚠️ {'; '.join(flags)}"
        parts.append(line)
    return "\n".join(parts)


def format_for_round2(quant_analysis: dict) -> str:
    """Format quant analysis as markdown to inject into Round 2 panel context."""
    if not quant_analysis or quant_analysis.get("error"):
        return ""
    lines = ["## Quantitative Financial Analysis\n"]
    summary = quant_analysis.get("summary", "")
    if summary:
        lines.append(summary)
        lines.append("")
    for model in quant_analysis.get("models", []):
        rec = model.get("recommendation", "")
        if not rec:
            continue
        lines.append(f"### {rec}")
        base = model.get("scenarios", {}).get("base", {})
        if base:
            lines.append(f"- Base revenue: ${base.get('annual_revenue', 0):,.0f}/yr | Net: ${base.get('net_contribution', 0):,.0f}/yr")
        if model.get("payback_months"):
            lines.append(f"- Payback: {model['payback_months']:.0f} months")
        if model.get("roi_percent") is not None:
            lines.append(f"- ROI: {model['roi_percent']:.0f}% | 3yr NPV: ${model.get('npv_3yr', 0):,.0f}")
        for flag in model.get("flags", []):
            lines.append(f"- ⚠️ {flag}")
        lines.append("")
    return "\n".join(lines)
