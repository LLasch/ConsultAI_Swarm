"""
Async pipeline orchestrator.

Wraps the 3-round consulting pipeline and emits SSE events onto an
asyncio.Queue so the /analyze endpoint can stream them to the client.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Optional

from api.models import AnalyzeRequest


async def run_analysis(request: AnalyzeRequest, queue: asyncio.Queue) -> None:
    """
    Orchestrate the full consulting pipeline, putting SSE event dicts onto
    `queue` as each stage completes.  Always ends with a "done" or "error"
    event so the SSE consumer knows when to close the stream.

    Event sequence:
        started → case_brief_started → case_brief_complete
        → retrieval_complete
        → round1_started → agent_complete (×N) → round1_complete
        → round2_started → panel_complete (×P) → round2_complete   [if rounds >= 2]
        → round3_started → consensus_complete                        [if rounds >= 3]
        → report_complete → done
    """
    try:
        case_dir = Path(request.case_path)
        if not case_dir.exists() or not case_dir.is_dir():
            await queue.put({"type": "error", "data": {"message": f"Case directory not found: {request.case_path}"}})
            return

        case_name = case_dir.name
        output_dir = Path(request.output_dir) / case_name
        effective_agents = min(request.agents, 20)

        estimated_cost = _estimate_cost(effective_agents, request.rounds)
        await queue.put({
            "type": "started",
            "data": {
                "case_name": case_name,
                "agents": effective_agents,
                "rounds": request.rounds,
                "estimated_cost": round(estimated_cost, 2),
            },
        })

        # ── Step 1: Load personas ─────────────────────────────────────────────
        personas_path = Path(__file__).parent.parent / "agents" / "personas.json"
        with open(personas_path, encoding="utf-8") as f:
            personas = json.load(f)[:effective_agents]

        # ── Step 2: Ingest case materials ─────────────────────────────────────
        await queue.put({"type": "case_brief_started", "data": {"case_name": case_name}})

        from ingestion.case_loader import load_case
        case_data = await asyncio.to_thread(load_case, case_dir)
        brief: str = case_data["brief"]

        await queue.put({
            "type": "case_brief_complete",
            "data": {"brief_preview": brief[:300]},
        })

        # ── Step 3: Retrieve past cases ───────────────────────────────────────
        from knowledge.retriever import retrieve_past_cases
        past_cases_text: str = await asyncio.to_thread(retrieve_past_cases, brief)

        similar_cases = [
            line.replace("###", "").strip()
            for line in past_cases_text.split("\n")
            if line.startswith("###")
        ]
        await queue.put({
            "type": "retrieval_complete",
            "data": {"similar_cases": similar_cases},
        })

        # ── Step 3b: Market research ──────────────────────────────────────────
        from agents.market_researcher import run_market_research

        await queue.put({"type": "market_research_started", "data": {}})
        market_context = await run_market_research(
            case_brief=brief,
            case_name=case_name,
            output_dir=output_dir,
            refresh=False,
        )
        await queue.put({
            "type": "market_research_complete",
            "data": {"has_data": bool(market_context.strip())},
        })

        # ── Step 4 & 5: Round 1 — individual agent analysis ───────────────────
        focus_question = request.question or "Provide a comprehensive analysis of this case."
        await queue.put({
            "type": "round1_started",
            "data": {"agent_count": len(personas)},
        })

        from agents.panel import run_round1
        round1_results = await run_round1(
            personas=personas,
            case_brief=brief,
            past_cases=past_cases_text,
            question=focus_question,
            output_dir=output_dir,
            event_queue=queue,
            market_context=market_context,
        )

        await queue.put({
            "type": "round1_complete",
            "data": {
                "agents_succeeded": len(round1_results),
                "agents_total": len(personas),
            },
        })

        if not round1_results:
            await queue.put({
                "type": "error",
                "data": {"message": "All agent calls failed. Check ANTHROPIC_API_KEY and connectivity."},
            })
            return

        # ── Step 6: Round 2 — panel deliberation ─────────────────────────────
        panel_results: list = []
        if request.rounds >= 2:
            num_panels = max(1, len(round1_results) // 5)
            await queue.put({
                "type": "round2_started",
                "data": {"panel_count": num_panels},
            })

            from agents.deliberation import run_round2
            panel_results = await run_round2(
                round1_results=round1_results,
                output_dir=output_dir,
                event_queue=queue,
            )

            await queue.put({
                "type": "round2_complete",
                "data": {"panels_succeeded": len(panel_results)},
            })

        # ── Step 7: Round 3 — consensus ───────────────────────────────────────
        consensus: dict = {}
        if request.rounds >= 3 and panel_results:
            await queue.put({"type": "round3_started", "data": {}})

            from agents.aggregator import run_round3
            consensus = await asyncio.to_thread(run_round3, panel_results, case_name, output_dir)

            await queue.put({
                "type": "consensus_complete",
                "data": {"consensus": consensus},
            })
        elif round1_results:
            # Fallback: quick consensus from Round 1 only (rounds < 3 or no panels)
            consensus = _quick_consensus(round1_results, len(round1_results))
            await queue.put({
                "type": "consensus_complete",
                "data": {"consensus": consensus},
            })

        # ── Step 7b: Chart planning ───────────────────────────────────────
        from deliverables.chart_planner import plan_charts, extract_financial_text

        financial_text = extract_financial_text(case_data)
        chart_plan = await asyncio.to_thread(
            plan_charts, brief, financial_text, consensus, market_context
        )
        await queue.put({
            "type": "chart_plan_complete",
            "data": {"chart_count": len(chart_plan)},
        })

        # ── Step 7c: Deliverables ─────────────────────────────────────────
        from deliverables.report_writer import write_report
        from deliverables.html_reporter import build_html_report

        await asyncio.to_thread(write_report, consensus, case_name, round1_results, output_dir)
        await asyncio.to_thread(
            build_html_report,
            consensus,
            case_name,
            round1_results,
            output_dir,
            None,   # red_team
            None,   # pushback
            None,   # quant_analysis
            None,   # directions
            None,   # case_tags
            chart_plan,
        )

        await queue.put({
            "type": "report_complete",
            "data": {"output_dir": str(output_dir)},
        })

        # ── Step 8: Archive ───────────────────────────────────────────────────
        if not request.no_archive:
            from archive import archive_case
            total_tokens = _estimate_tokens(effective_agents, request.rounds)
            await asyncio.to_thread(
                archive_case,
                case_name=case_name,
                active_dir=case_dir,
                output_dir=output_dir,
                consensus=consensus,
                n_agents=len(personas),
                n_rounds=request.rounds,
                question=request.question or "",
                total_tokens=total_tokens,
            )

        await queue.put({"type": "done", "data": {}})

    except Exception as e:
        await queue.put({"type": "error", "data": {"message": str(e)}})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_cost(agents: int, rounds: int) -> float:
    r1 = agents * 2000 / 1_000_000 * 3.0
    r2 = (agents // 5) * 4000 / 1_000_000 * 3.0 if rounds >= 2 else 0
    r3 = 8000 / 1_000_000 * 3.0 if rounds >= 3 else 0
    return r1 + r2 + r3


def _estimate_tokens(agents: int, rounds: int) -> int:
    r1 = agents * 2000
    r2 = (agents // 5) * 4000 if rounds >= 2 else 0
    r3 = 8000 if rounds >= 3 else 0
    return r1 + r2 + r3


def _quick_consensus(round1_results: list, n_agents: int) -> dict:
    """Minimal consensus from Round 1 only — used when rounds < 3 or panels failed."""
    all_recs = [r for a in round1_results for r in a.get("analysis", {}).get("recommendations", [])]
    all_problems = [p for a in round1_results for p in a.get("analysis", {}).get("key_problems", [])]
    title_counts = Counter(r.get("title", "") for r in all_recs if r.get("title"))
    top_titles = [t for t, _ in title_counts.most_common(5)]

    top_recs = []
    seen: set = set()
    for title in top_titles:
        for rec in all_recs:
            if rec.get("title") == title and title not in seen:
                top_recs.append({
                    **rec,
                    "rank": len(top_recs) + 1,
                    "panel_support": f"{title_counts[title]}/{n_agents} agents",
                })
                seen.add(title)
                break

    key_insights = [
        a.get("analysis", {}).get("key_insight", "")
        for a in round1_results
        if a.get("analysis", {}).get("key_insight")
    ]
    return {
        "executive_summary": f"Analysis by {n_agents} consultants identified {len(top_recs)} key recommendations.",
        "problem_statement": all_problems[0] if all_problems else "See key findings.",
        "analysis_framework": "Multi-expert independent analysis",
        "key_findings": [{"finding": p, "evidence": "", "confidence": 0.7} for p in set(all_problems[:4])],
        "recommendations": top_recs,
        "risk_assessment": "See full agent log for risk assessments.",
        "minority_views": [],
        "implementation_roadmap": {
            "phase_1_0_3_months": [],
            "phase_2_3_6_months": [],
            "phase_3_6_12_months": [],
        },
        "missing_information": [],
        "bottom_line": key_insights[0] if key_insights else "See recommendations.",
    }
