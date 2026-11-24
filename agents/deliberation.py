"""Round 2 — Panel deliberation. Groups agents into panels and deliberates."""

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

import httpx
import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeElapsedColumn

logger = logging.getLogger(__name__)
console = Console(file=sys.stdout)

PANEL_SYSTEM = """You are facilitating a consulting panel discussion between 5 consultants. They have each independently analyzed a business case. Your job is to:
1. Identify where they agree (these are high-confidence findings)
2. Identify where they disagree and evaluate both sides
3. Challenge weak reasoning — if a recommendation lacks evidence, call it out
4. Synthesize a refined set of 3-5 recommendations that the panel endorses
5. Note any strong dissents that shouldn't be lost

Respond ONLY with valid JSON in this exact structure (no markdown fences, no extra text):
{
  "consensus_recommendations": [
    {
      "title": "recommendation title",
      "description": "what to do and why",
      "confidence": 0.8,
      "impact": "high",
      "feasibility": "high",
      "timeline": "short-term",
      "supporting_experts": ["names of agents who endorsed this"],
      "key_evidence": "what evidence supports this"
    }
  ],
  "confidence_level": "high",
  "key_agreements": ["what the panel strongly agrees on"],
  "key_disagreements": ["unresolved tensions"],
  "strongest_dissent": "the best argument against the consensus",
  "evidence_gaps": ["what data would change the recommendation"]
}"""


async def run_round2(
    round1_results: list,
    output_dir: Path = Path("output"),
    panel_size: int = 5,
    event_queue=None,  # asyncio.Queue | None — if set, emits "panel_complete" events
    directions: list = None,  # list of direction dicts — enables cross-team debate panels
    quant_context: str = "",  # quantitative analysis text to inject into panel prompts
) -> list:
    """
    Group agents into panels of 5, run deliberation for each panel.
    Returns list of panel results.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    num_agents = len(round1_results)
    num_panels = max(1, num_agents // panel_size)

    console.print(f"\n[bold cyan][8/12] Round 2 — Panel Deliberation ({num_panels} panels)...[/bold cyan]")

    if directions:
        panels = _form_cross_team_panels(round1_results, directions, num_panels)
        console.print(f"  [dim]→ Cross-team debate: one agent per direction per panel[/dim]")
    else:
        panels = _form_panels(round1_results, num_panels, panel_size)
    start = time.time()

    # Brief pause after Round 1 to let rate limits recover
    await asyncio.sleep(5)

    results = []
    BATCH_SIZE = 3  # run 3 panels at a time to stay within rate limits
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  Deliberating", total=len(panels))
        for i in range(0, len(panels), BATCH_SIZE):
            batch = panels[i : i + BATCH_SIZE]
            panel_tasks = [_deliberate_panel(api_key, i + j + 1, panel, quant_context=quant_context) for j, panel in enumerate(batch)]
            panel_results = await asyncio.gather(*panel_tasks, return_exceptions=True)
            for r in panel_results:
                if isinstance(r, Exception):
                    logger.error(f"Panel deliberation failed: {r}")
                else:
                    results.append(r)
                    if event_queue is not None:
                        await event_queue.put({"type": "panel_complete", "data": r})
                progress.advance(task)
            if i + BATCH_SIZE < len(panels):
                await asyncio.sleep(4)

    # Aggregate stats
    all_recs = [r for panel in results for r in panel.get("result", {}).get("consensus_recommendations", [])]
    console.print(f"  → Consolidated to {len(all_recs)} recommendations across panels")

    disagreements = [d for panel in results for d in panel.get("result", {}).get("key_disagreements", [])]
    if disagreements:
        console.print(f"  → Key disagreements: {'; '.join(disagreements[:2])}")

    # Save
    output_path = output_dir / "round2_panels.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"panels": results, "elapsed_seconds": time.time() - start}, f, indent=2)

    return results


def _form_panels(agents: list, num_panels: int, panel_size: int) -> list:
    """
    Form balanced panels ensuring diversity of expertise, thinking styles,
    seniority levels, and at least one dissenting voice per panel.
    """
    if not agents:
        return []

    # Identify outliers (agents whose recommendations diverge from mode)
    all_top_recs = []
    for agent in agents:
        recs = agent.get("analysis", {}).get("recommendations", [])
        if recs:
            all_top_recs.append(recs[0].get("title", "").lower())

    from collections import Counter
    rec_counts = Counter(all_top_recs)
    mode_rec = rec_counts.most_common(1)[0][0] if rec_counts else ""

    # Tag outliers
    for agent in agents:
        recs = agent.get("analysis", {}).get("recommendations", [])
        top = recs[0].get("title", "").lower() if recs else ""
        agent["_is_outlier"] = mode_rec and top and top != mode_rec

    # Sort agents for distribution
    seniors = [a for a in agents if a.get("seniority") == "senior"]
    juniors = [a for a in agents if a.get("seniority") == "junior"]
    mids = [a for a in agents if a.get("seniority") == "mid"]
    outliers = [a for a in agents if a.get("_is_outlier")]

    panels = [[] for _ in range(num_panels)]

    # Distribute seniors evenly
    random.shuffle(seniors)
    for i, agent in enumerate(seniors):
        panels[i % num_panels].append(agent)

    # Distribute outliers to panels that don't have one
    random.shuffle(outliers)
    for panel in panels:
        if not any(a.get("_is_outlier") for a in panel) and outliers:
            panels[panels.index(panel)].append(outliers.pop(0))

    # Fill remaining slots with mids and juniors
    remaining = [a for a in mids + juniors if a not in [x for p in panels for x in p]]
    random.shuffle(remaining)
    for i, agent in enumerate(remaining):
        # Add to smallest panel
        smallest = min(panels, key=len)
        if len(smallest) < panel_size:
            smallest.append(agent)

    # Trim to panel_size
    return [p[:panel_size] for p in panels if p]


def _form_cross_team_panels(round1_results: list, directions: list, num_panels: int) -> list:
    """
    Form debate panels where each panel has one agent from each strategic direction team.
    This ensures every panel evaluates all directions head-to-head.
    """
    # Group agents by their assigned direction
    direction_buckets: dict = {d["direction"]: [] for d in directions}
    unassigned = []
    for agent in round1_results:
        direction = agent.get("team_direction")
        if direction and direction in direction_buckets:
            direction_buckets[direction].append(agent)
        else:
            unassigned.append(agent)

    # Build panels by taking one from each bucket
    panels = []
    max_panels = max(len(bucket) for bucket in direction_buckets.values()) if direction_buckets else 1
    actual_panels = min(max_panels, num_panels)

    for i in range(actual_panels):
        panel = []
        for direction, bucket in direction_buckets.items():
            if i < len(bucket):
                panel.append(bucket[i])
        # Fill remaining slots from unassigned agents
        for agent in unassigned:
            if len(panel) >= 5:
                break
            if agent not in panel:
                panel.append(agent)
        if panel:
            panels.append(panel)

    return panels


async def _deliberate_panel(api_key: str, panel_num: int, agents: list, quant_context: str = "", max_retries: int = 5) -> dict:
    """Run a single panel deliberation."""
    agent_sections = []
    for agent in agents:
        analysis = agent.get("analysis", {})
        direction_note = f" [Arguing for: {agent['team_direction']}]" if agent.get("team_direction") else ""
        agent_sections.append(f"""### {agent['name']} ({', '.join(agent.get('expertise', []))}){direction_note}
Key Problems: {json.dumps(analysis.get('key_problems', []))}
Recommendations: {json.dumps(analysis.get('recommendations', [])[:3])}
Key Insight: {analysis.get('key_insight', 'N/A')}
Dissenting View: {analysis.get('dissenting_view', 'N/A')}""")

    user_content = "## Agent Analyses\n\n" + "\n\n".join(agent_sections)
    if quant_context:
        user_content += f"\n\n{quant_context}"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "system": PANEL_SYSTEM,
        "messages": [{"role": "user", "content": user_content}],
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text = data["content"][0]["text"]
                result = _parse_json(text)
                return {
                    "panel_num": panel_num,
                    "agents": [a["name"] for a in agents],
                    "result": result,
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await asyncio.sleep(2 ** attempt * 5)
                last_error = f"Rate limited (attempt {attempt+1})"
            else:
                last_error = f"HTTP {e.response.status_code}"
                break
        except Exception as e:
            await asyncio.sleep(2 ** attempt)
            last_error = str(e)

    return {"panel_num": panel_num, "agents": [a["name"] for a in agents], "error": last_error, "result": {}}


def _parse_json(text: str) -> dict:
    """Parse JSON from response text."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"parse_error": True, "raw": text[:300]}
