"""Round 1 — Individual agent analysis. Fires all 50 agents concurrently."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

logger = logging.getLogger(__name__)
console = Console(file=sys.stdout)

FRAMEWORK_ASSIGNMENTS = {
    "strategy": "Structure your analysis using Porter's Five Forces and the Ansoff Matrix.",
    "finance": "Structure your analysis using the Profitability Framework (Revenue = Volume × Price, Costs = Fixed + Variable). Show the math wherever possible.",
    "operations": "Structure your analysis using Value Chain Analysis. Identify which activities create the most value and which are most inefficient.",
    "marketing": "Structure your analysis using Customer Segmentation (identify 3-5 segments with size, current penetration, and value) and Jobs to Be Done.",
    "hr": "Structure your analysis using McKinsey 7S. Assess all 7 elements and identify misalignments.",
    "risk": "Structure your analysis as a Pre-Mortem. Assume each major recommendation has FAILED and explain why.",
    "nonprofit": "Structure your analysis using a sustainability matrix: which programs generate surplus, which require subsidy, and what's the cross-subsidy model?",
    "museum": "Structure your analysis around the visitor experience lifecycle: awareness → first visit → repeat visit → membership conversion → advocacy.",
    "membership": "Structure your analysis using membership unit economics: acquisition cost, retention rate, upgrade rate, lifetime value, and churn drivers.",
    "technology": "Structure your analysis using the Technology Adoption Lifecycle. Identify where this organization sits and what that means for digital strategy.",
    "revenue_models": "Map all current and potential revenue streams using a Revenue Model Canvas. Quantify each stream's potential.",
    "saas": "Apply SaaS metrics thinking: CAC, LTV, churn, NRR. Which of these levers has the most impact here?",
    "retail": "Apply retail unit economics: traffic, conversion, average order value, margin, and inventory turns.",
    "education": "Structure your analysis around program sustainability: which programs are self-funding, which are subsidized, and what is the enrollment/revenue model?",
    "healthcare": "Apply healthcare operations frameworks: capacity utilization, service line profitability, and payer mix analysis.",
    "legal": "Identify regulatory constraints, compliance requirements, contractual risks, and legal barriers for each recommendation.",
    "creative": "Structure your analysis around Jobs to Be Done — what jobs are customers/beneficiaries hiring this organization to do, and how could that be reframed?",
    "default": "Apply the most relevant consulting framework(s) to structure your analysis.",
}

ROUND1_SYSTEM = """You are {name}. {persona}

You are part of a consulting panel analyzing a business case. Read the case materials carefully and provide your independent analysis. Do not hedge excessively — take clear positions.

ANALYSIS FRAMEWORK: {framework_instruction}

Respond ONLY with valid JSON in this exact structure (no markdown fences, no extra text):
{{
  "key_problems": ["string array of 2-4 core problems you identify"],
  "root_cause_analysis": "1-2 paragraphs on what is actually driving these problems",
  "recommendations": [
    {{
      "title": "short name",
      "description": "what to do and why",
      "confidence": 0.8,
      "impact": "high",
      "feasibility": "high",
      "timeline": "short-term",
      "risks": "key risks of this recommendation"
    }}
  ],
  "dissenting_view": "what might a reasonable person disagree with in your analysis?",
  "priority_ranking": ["rec titles in order of priority"],
  "missing_information": ["what would you want to know that isn't in the materials?"],
  "key_insight": "the single most important thing the client needs to hear"
}}"""

ROUND1_USER = """## Case Brief
{case_brief}

## Market Research
{market_context}

## Relevant Past Cases
{past_cases}

## Analysis Question
{question}"""


async def run_round1(
    personas: list,
    case_brief: str,
    past_cases: str = "",
    question: str = "Provide a comprehensive analysis of this case.",
    output_dir: Path = Path("output"),
    batch_size: int = 5,
    event_queue=None,  # asyncio.Queue | None — if set, emits "agent_complete" events
    teams: list = None,  # list of {"direction", "description", "agents"} — enables competing teams mode
    market_context: str = "",
) -> list:
    """
    Fire all agents concurrently (batched), return list of agent results.
    When teams is provided, runs agents in direction-advocacy mode (Upgrade 2).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    results = []
    failed = []

    output_dir.mkdir(parents=True, exist_ok=True)

    # Flatten teams into (persona, team_direction) pairs, or use personas directly
    if teams:
        agent_pairs = [
            (agent, {"direction": team["direction"], "description": team["description"]})
            for team in teams
            for agent in team["agents"]
        ]
        n_total = len(agent_pairs)
        console.print(f"\n[bold cyan][4/12] Round 1 — Competing Teams ({len(teams)} directions × ~{n_total // len(teams)} agents)...[/bold cyan]")
        for team in teams:
            console.print(f"  [dim]→ Team '{team['direction']}': {', '.join(a['name'] for a in team['agents'][:3])}{'...' if len(team['agents']) > 3 else ''}[/dim]")
    else:
        agent_pairs = [(p, None) for p in personas]
        n_total = len(personas)
        console.print(f"\n[bold cyan][4/12] Round 1 — Individual Analysis ({n_total} agents)...[/bold cyan]")

    start = time.time()

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  Analyzing", total=n_total)

        # Process in batches to respect rate limits
        for i in range(0, n_total, batch_size):
            batch = agent_pairs[i : i + batch_size]
            batch_tasks = [
                _call_agent(api_key, persona, case_brief, past_cases, question, team_direction=direction, market_context=market_context)
                for persona, direction in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Pause between batches to stay within rate limits
            if i + batch_size < n_total:
                await asyncio.sleep(12)

            for (persona, direction), result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Agent {persona['name']} failed: {result}")
                    failed.append({"id": persona["id"], "name": persona["name"], "error": str(result)})
                elif result.get("error"):
                    failed.append({"id": persona["id"], "name": persona["name"], "error": result["error"]})
                else:
                    if direction:
                        result["team_direction"] = direction["direction"]
                    results.append(result)
                    if event_queue is not None:
                        await event_queue.put({
                            "type": "agent_complete",
                            "data": {
                                "id": result["id"],
                                "name": result["name"],
                                "expertise": result.get("expertise", []),
                                "seniority": result.get("seniority", ""),
                                "thinking_style": result.get("thinking_style", ""),
                                "key_insight": result.get("analysis", {}).get("key_insight", ""),
                                "key_problems": result.get("analysis", {}).get("key_problems", []),
                                "recommendations": result.get("analysis", {}).get("recommendations", []),
                                "dissenting_view": result.get("analysis", {}).get("dissenting_view", ""),
                                "team_direction": direction["direction"] if direction else None,
                            },
                        })
                progress.advance(task)

    elapsed = time.time() - start
    all_recs = [r for agent in results for r in agent.get("analysis", {}).get("recommendations", [])]
    unique_titles = set(r.get("title", "") for r in all_recs)

    console.print(f"  → {len(unique_titles)} unique recommendations generated")
    if failed:
        console.print(f"  [yellow]→ {len(failed)} agents failed and were skipped[/yellow]")

    # Summarize top themes
    all_problems = [p for agent in results for p in agent.get("analysis", {}).get("key_problems", [])]
    _print_top_themes(all_problems)

    # Save results
    output_path = output_dir / "round1_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "failed": failed, "elapsed_seconds": elapsed}, f, indent=2)

    return results


async def _call_agent(
    api_key: str,
    persona: dict,
    case_brief: str,
    past_cases: str,
    question: str,
    team_direction: dict = None,
    max_retries: int = 5,
    market_context: str = "",
) -> dict:
    """Make a single agent API call with retry logic."""
    primary_exp = persona.get("expertise", ["default"])[0]
    framework_instruction = FRAMEWORK_ASSIGNMENTS.get(primary_exp, FRAMEWORK_ASSIGNMENTS["default"])

    system = ROUND1_SYSTEM.format(
        name=persona["name"],
        persona=persona["persona"],
        framework_instruction=framework_instruction,
    )

    if team_direction:
        system += (
            f"\n\nSTRATEGIC DIRECTION ASSIGNMENT: You have been assigned to argue for the following "
            f"strategic direction: **{team_direction['direction']}** — {team_direction['description']}\n\n"
            "Make the STRONGEST POSSIBLE CASE for this direction. Find the evidence that supports it. "
            "Build the implementation path. Even if you personally believe another direction might be "
            "better, argue for this one with conviction. The deliberation rounds will determine which "
            "direction wins on the merits."
        )
    _market_section = (
        market_context.strip()
        if market_context and market_context.strip()
        else "No market research available for this case."
    )
    user = ROUND1_USER.format(
        case_brief=case_brief[:5000],  # keep input budget tight
        market_context=_market_section[:1500],  # cap at ~1,500 tokens
        past_cases=past_cases or "No past cases available.",
        question=question,
    )

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text = data["content"][0]["text"]

                # Parse JSON response
                analysis = _parse_json_response(text)

                return {
                    "id": persona["id"],
                    "name": persona["name"],
                    "expertise": persona["expertise"],
                    "thinking_style": persona["thinking_style"],
                    "seniority": persona["seniority"],
                    "analysis": analysis,
                    "raw": text,
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Respect Anthropic's retry-after header if present, else exponential backoff
                retry_after = e.response.headers.get("retry-after")
                wait = float(retry_after) if retry_after else (2 ** attempt) * 5
                logger.warning("Rate limited; waiting %.0fs (attempt %d)", wait, attempt + 1)
                await asyncio.sleep(wait)
                last_error = f"Rate limited (attempt {attempt+1})"
            else:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                break
        except Exception as e:
            wait = 2 ** attempt
            await asyncio.sleep(wait)
            last_error = str(e)

    return {
        "id": persona["id"],
        "name": persona["name"],
        "error": last_error,
        "analysis": {},
    }


def _parse_json_response(text: str) -> dict:
    """Parse JSON from agent response, handling common formatting issues."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        import re
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"parse_error": True, "raw_text": text[:500]}


def _print_top_themes(problems: list):
    """Print the top recurring themes from agent key_problems."""
    from collections import Counter
    import re
    words = []
    for p in problems:
        words.extend(re.findall(r'\b[a-z]{4,}\b', p.lower()))
    stopwords = {"that", "with", "from", "this", "have", "they", "will", "been", "their", "more", "than"}
    counts = Counter(w for w in words if w not in stopwords)
    top = [w for w, _ in counts.most_common(5)]
    if top:
        console.print(f"  → Top themes: {', '.join(top)}")
