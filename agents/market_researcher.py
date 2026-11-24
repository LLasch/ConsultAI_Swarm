"""
market_researcher.py — Auto-researches market data before agents analyze a case.

Pipeline:
  1. identify_research_needs  — 1 Sonnet call: reads brief → returns 5 search queries
  2. execute_research_queries  — 5 parallel Sonnet calls with web search
  3. compile_market_context    — pure Python → returns markdown string + saves file

The resulting market_context.md is injected into every Round 1 agent's prompt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
_MODEL = "claude-sonnet-4-20250514"

# ── Agentic tool-use loop ─────────────────────────────────────────────────────

def _run_agentic(client, *, messages: list, tools: list, max_tokens: int = 2000, max_turns: int = 8) -> str:
    """
    Run a Sonnet call with tool-use support, looping until stop_reason = 'end_turn'.
    Returns the final text response.
    """
    msgs = list(messages)
    for _ in range(max_turns):
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=max_tokens,
            tools=tools,
            messages=msgs,
        )

        # Append assistant turn (content is a list of blocks from the SDK)
        msgs.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            # Extract final text block
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    return block.text
            return ""

        # Build tool_result messages for any tool_use blocks
        tool_results = []
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                # web_search_20250305 results are embedded in the block by Anthropic;
                # send an empty tool_result to keep the conversation going.
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "",
                })
        if tool_results:
            msgs.append({"role": "user", "content": tool_results})

    logger.warning("market_researcher: agentic loop hit max_turns without end_turn")
    return ""


def _strip_fences(text: str) -> str:
    """Remove ```json / ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text, count=1)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


# ── Step 1: Identify research needs ──────────────────────────────────────────

def identify_research_needs(client, case_brief: str) -> list[dict]:
    """
    Ask Sonnet to identify the 5 most valuable market data points to find.
    Returns a list of {"data_needed", "search_query", "why"} dicts.
    """
    prompt = f"""Read this consulting case brief and identify the 5 most important
pieces of market data that would strengthen the analysis.

For each, provide a specific search query that would find the data.

Case Brief:
{case_brief[:5000]}

Respond ONLY with a JSON array — no markdown fences, no extra text:
[
  {{
    "data_needed": "size of the Canadian museum membership market",
    "search_query": "Canadian museum membership revenue market size 2024",
    "why": "needed to benchmark MOA's membership potential against industry"
  }}
]

Focus on:
- Industry/sector market size and growth rate
- Comparable organizations and their revenue models
- Benchmarks (average revenue per member, conversion rates, cost per acquisition, etc.)
- Regional economic data relevant to the client's location
- Competitor landscape and pricing
- Relevant trends (demographic shifts, funding changes, consumer behavior)

Do NOT search for generic business advice. Search for specific numbers,
benchmarks, and data points that the consulting agents can cite in their analysis."""

    text = _run_agentic(
        client,
        messages=[{"role": "user", "content": prompt}],
        tools=[_WEB_SEARCH_TOOL],
        max_tokens=1200,
    )
    try:
        queries = json.loads(_strip_fences(text))
        if isinstance(queries, list):
            return queries[:5]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("identify_research_needs: JSON parse failed (%s). Raw: %s", exc, text[:300])
    return []


# ── Step 2: Execute a single research query ───────────────────────────────────

def _execute_one_query(client, query_spec: dict) -> dict:
    """
    Run one Sonnet + web search call for a specific query.
    Returns {"query", "findings": [...], "summary", "data_gap": bool}
    """
    query = query_spec.get("search_query", "")
    context = query_spec.get("why", "")

    prompt = f"""Search for this specific market data and extract concrete numbers,
statistics, and benchmarks.

Query: {query}
Context: {context}

Search thoroughly. Prefer government sources, industry associations, and research
firms over blogs. Use the most recent data available.

Respond ONLY with a JSON object — no markdown fences, no extra text:
{{
  "query": "{query}",
  "findings": [
    {{
      "data_point": "the specific number or statistic",
      "source": "where this data comes from (organization name)",
      "year": "what year the data is from",
      "relevance": "one sentence on why this matters for the case"
    }}
  ],
  "summary": "2-3 sentence synthesis of what this data means for the client",
  "data_gap": false
}}

Set "data_gap": true and leave "findings" empty if you cannot find reliable data.
Do NOT fabricate numbers. If the data isn't available, say so."""

    text = _run_agentic(
        client,
        messages=[{"role": "user", "content": prompt}],
        tools=[_WEB_SEARCH_TOOL],
        max_tokens=1800,
    )
    try:
        result = json.loads(_strip_fences(text))
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("execute_one_query: JSON parse failed for '%s' (%s)", query, exc)
    return {"query": query, "findings": [], "summary": "", "data_gap": True}


# ── Step 3: Compile market context ───────────────────────────────────────────

def compile_market_context(research_results: list[dict], case_name: str) -> str:
    """
    Turn research results into a concise market_context.md string.
    Targets < 1,500 tokens so it fits cleanly in each agent's prompt.
    """
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"# Market Research Context", f"*Auto-generated on {today}*", ""]

    # Gather all findings grouped
    all_findings = []
    gaps = []
    summaries = []

    for r in research_results:
        if r.get("data_gap"):
            gaps.append(r.get("query", "Unknown query"))
            continue
        findings = r.get("findings") or []
        if findings:
            all_findings.extend(findings)
        summary = r.get("summary", "").strip()
        if summary:
            summaries.append(summary)

    # Industry Overview — pull top summaries
    if summaries:
        lines.append("## Industry Overview")
        for s in summaries[:3]:
            lines.append(f"- {s}")
        lines.append("")

    # Key Data Points — every concrete finding with source
    if all_findings:
        lines.append("## Key Data Points")
        # Limit to most relevant 15 findings to stay under token budget
        for f in all_findings[:15]:
            dp = f.get("data_point", "").strip()
            source = f.get("source", "").strip()
            year = f.get("year", "").strip()
            relevance = f.get("relevance", "").strip()
            if dp:
                source_str = f" ({source}, {year})" if source and year else (f" ({source})" if source else "")
                lines.append(f"- {dp}{source_str}")
                if relevance:
                    lines.append(f"  *{relevance}*")
        lines.append("")

    # Data Gaps
    if gaps:
        lines.append("## Data Gaps")
        lines.append("*Could not find reliable data for:*")
        for g in gaps:
            lines.append(f"- {g}")
        lines.append("")

    if not all_findings and not summaries:
        lines.append("*Market research did not return usable data for this case.*")
        lines.append("")

    return "\n".join(lines)


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_market_research(
    case_brief: str,
    case_name: str,
    output_dir: Path,
    refresh: bool = False,
) -> str:
    """
    Full market research pipeline. Returns compiled market_context string.
    Caches to output_dir/market_context.md; skips research if cache exists
    and refresh=False.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / "market_context.md"

    if cache_path.exists() and not refresh:
        logger.info("market_researcher: using cached %s", cache_path)
        return cache_path.read_text(encoding="utf-8")

    try:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv()

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Step 1: identify what to search for
        logger.info("market_researcher: identifying research needs...")
        query_specs = await asyncio.to_thread(identify_research_needs, client, case_brief)

        if not query_specs:
            logger.warning("market_researcher: no research queries identified")
            return ""

        logger.info("market_researcher: %d queries identified, executing in parallel...", len(query_specs))

        # Step 2: run all queries concurrently (with small stagger to avoid rate limits)
        async def _staggered(spec: dict, delay: float) -> dict:
            if delay > 0:
                await asyncio.sleep(delay)
            return await asyncio.to_thread(_execute_one_query, client, spec)

        tasks = [_staggered(spec, i * 0.5) for i, spec in enumerate(query_specs)]
        research_results = await asyncio.gather(*tasks)

        # Step 3: compile
        market_context = compile_market_context(list(research_results), case_name)

        # Save cache
        cache_path.write_text(market_context, encoding="utf-8")
        logger.info("market_researcher: market_context.md written to %s", cache_path)

        return market_context

    except Exception as exc:
        logger.warning("market_researcher: research failed (%s); proceeding without market data.", exc)
        return ""
