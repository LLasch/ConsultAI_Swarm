#!/usr/bin/env python3
"""
Consulting Swarm — Multi-agent consulting analysis engine.

Usage:
  python main.py analyze ./cases/active/moa/
  python main.py analyze ./cases/active/moa/ --question "Should we pursue corporate memberships or event rentals first?"
  python main.py analyze ./cases/active/moa/ --agents 10 --rounds 2
  python main.py analyze ./cases/active/moa/ --no-archive
  python main.py learn ./cases/past/ymca-membership/ --industry nonprofit --type revenue_diversification
  python main.py outcome moa "Corporate membership launched Q3 2026, 12 members, $47K revenue."
  python main.py cases
"""

import asyncio
import io
import json
import os
import signal
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows so Unicode console chars don't crash
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.rule import Rule

load_dotenv()

app = typer.Typer(
    help="Consulting Swarm — Multi-agent consulting analysis engine",
    add_completion=False,
)
console = Console(file=sys.stdout)

_interrupted = False


def _handle_interrupt(sig, frame):
    global _interrupted
    _interrupted = True
    console.print("\n\n[yellow]Interrupted. Saving progress...[/yellow]")


signal.signal(signal.SIGINT, _handle_interrupt)


@app.command()
def analyze(
    case_dir: Path = typer.Argument(..., help="Path to the case materials directory"),
    question: str = typer.Option(None, "--question", "-q", help="Specific strategic question to focus on"),
    agents: int = typer.Option(20, "--agents", "-n", help="Number of consultant agents (default: 20)"),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of deliberation rounds (default: 3)"),
    output: Path = typer.Option(Path("output"), "--output", "-o", help="Output directory"),
    no_archive: bool = typer.Option(False, "--no-archive", help="Skip auto-archiving after analysis"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip cost confirmation prompt"),
    refresh_market: bool = typer.Option(False, "--refresh-market", help="Re-run market research even if cached"),
):
    """Run a full multi-agent consulting analysis on a case directory."""
    _check_api_key()

    if not case_dir.exists() or not case_dir.is_dir():
        console.print(f"[red]Error: {case_dir} is not a valid directory[/red]")
        raise typer.Exit(1)

    case_name = case_dir.name
    output_dir = output / case_name

    console.print(Rule("[bold blue]Consulting Swarm Analysis[/bold blue]"))
    console.print()

    effective_agents = min(agents, 20)
    estimated_cost = _estimate_cost(effective_agents, rounds)
    console.print(f"[dim]Estimated cost: ${estimated_cost:.2f}  |  Agents: {effective_agents}  |  Rounds: {rounds}[/dim]")

    if not yes:
        proceed = typer.confirm("Proceed?", default=True)
        if not proceed:
            raise typer.Exit(0)

    start_total = time.time()

    # ── Step 1: Load all personas ─────────────────────────────────────────
    all_personas = _load_personas(50)  # always load full roster for selection
    console.print(f"  -> Loaded {len(all_personas)} personas from roster")

    # ── Step 2: Ingest case materials ─────────────────────────────────────
    from ingestion.case_loader import load_case
    try:
        case_data = load_case(case_dir, console=console)
    except Exception as e:
        console.print(f"[red]Failed to load case materials: {e}[/red]")
        raise typer.Exit(1)

    brief = case_data["brief"]

    # ── Step 3: Select specialist panel ───────────────────────────────────
    console.print(f"\n[bold cyan][2/12] Selecting specialist panel...[/bold cyan]")
    case_tags = []
    personas = all_personas[:effective_agents]  # fallback
    try:
        from agents.selector import select_panel
        personas, case_tags = select_panel(brief, all_personas, n_agents=effective_agents)
        console.print(f"  -> Case tags: {', '.join(case_tags)}")
        console.print(f"  -> Selected {len(personas)} specialists")
        _print_persona_breakdown(personas)
    except Exception as e:
        console.print(f"  [yellow]Panel selection failed ({e}), using default order[/yellow]")

    # ── Step 4: Retrieve past cases ────────────────────────────────────────
    console.print("\n[bold cyan][3/12] Retrieving relevant past cases...[/bold cyan]")
    from knowledge.retriever import retrieve_past_cases
    past_cases_text = retrieve_past_cases(brief)
    if "No past cases" not in past_cases_text and "failed" not in past_cases_text:
        for line in past_cases_text.split("\n"):
            if line.startswith("###"):
                ref = line.replace("###", "").strip()
                console.print(f'  -> Found similar case: "{ref}"')
    else:
        console.print(f"  -> {past_cases_text.split(chr(10))[0]}")

    # ── Step 4b: Market research ───────────────────────────────────────────
    console.print("\n[bold cyan][3b/12] Researching market data...[/bold cyan]")
    market_context = ""
    try:
        from agents.market_researcher import run_market_research
        market_context = asyncio.run(
            run_market_research(brief, case_name, output_dir, refresh=refresh_market)
        )
        if market_context.strip():
            n_points = market_context.count("\n- ")
            console.print(f"  -> Market research complete ({n_points} data points found)")
        else:
            console.print("  [dim]-> No market data found for this case[/dim]")
    except Exception as e:
        console.print(f"  [yellow]Market research failed ({e}), continuing without[/yellow]")

    # ── Step 5: Generate competing strategic directions ───────────────────
    console.print(f"\n[bold cyan][4/12] Generating competing strategic directions...[/bold cyan]")
    directions = []
    teams = None
    try:
        from agents.strategizer import generate_strategic_directions, assign_teams
        directions = generate_strategic_directions(brief)
        teams = assign_teams(personas, directions)
        for i, d in enumerate(directions, 1):
            console.print(f"  -> Direction {i}: {d['direction']} — {d['description']}")
    except Exception as e:
        console.print(f"  [yellow]Direction generation failed ({e}), running independent analysis[/yellow]")

    # ── Step 6: Load agent confidence weights ─────────────────────────────
    agent_weights = {}
    try:
        from knowledge.confidence_tracker import get_agent_weights
        agent_weights = get_agent_weights(personas)
        weighted = {k: v for k, v in agent_weights.items() if v != 1.0}
        if weighted:
            console.print(f"  [dim]-> {len(weighted)} agents have historical accuracy weights[/dim]")
    except Exception:
        pass

    # ── Step 7: Round 1 ───────────────────────────────────────────────────
    focus_question = question or "Provide a comprehensive analysis of this case."
    from agents.panel import run_round1
    round1_results = asyncio.run(
        run_round1(
            personas=personas,
            case_brief=brief,
            past_cases=past_cases_text,
            question=focus_question,
            output_dir=output_dir,
            teams=teams,
            market_context=market_context,
        )
    )

    if _interrupted:
        _save_partial(output_dir, round1_results=round1_results)
        raise typer.Exit(0)

    if not round1_results:
        console.print("[red]All agent calls failed. Check your API key and connectivity.[/red]")
        raise typer.Exit(1)

    # ── Step 8: Quantitative modeling ─────────────────────────────────────
    quant_analysis = {}
    console.print(f"\n[bold cyan][7/12] Running quantitative financial models...[/bold cyan]")
    try:
        from agents.quant_model import run_quantitative_analysis, format_for_round2
        quant_analysis = run_quantitative_analysis(brief, round1_results, output_dir)
        if quant_analysis.get("models"):
            console.print(f"  -> Modeled {len(quant_analysis['models'])} recommendations")
        quant_context = format_for_round2(quant_analysis)
    except Exception as e:
        console.print(f"  [yellow]Quantitative modeling failed ({e}), continuing without[/yellow]")
        quant_context = ""

    # ── Step 9: Round 2 ────────────────────────────────────────────────────
    panel_results = []
    if rounds >= 2:
        from agents.deliberation import run_round2
        panel_results = asyncio.run(
            run_round2(
                round1_results=round1_results,
                output_dir=output_dir,
                directions=directions if teams else None,
                quant_context=quant_context,
            )
        )
        if _interrupted:
            _save_partial(output_dir, round1_results=round1_results, panel_results=panel_results)
            raise typer.Exit(0)

    # ── Step 10: Round 3 ──────────────────────────────────────────────────
    consensus = {}
    if rounds >= 3 and panel_results:
        from agents.aggregator import run_round3
        consensus = run_round3(panel_results=panel_results, case_name=case_name, output_dir=output_dir)
    elif round1_results:
        consensus = _quick_consensus(round1_results)

    # ── Step 11: Client pushback + revision ───────────────────────────────
    pushback_result = {}
    console.print(f"\n[bold cyan][10/12] Running client pushback simulation...[/bold cyan]")
    try:
        from agents.pushback import run_pushback_round
        pushback_result, revised_consensus = run_pushback_round(consensus, brief, output_dir)
        if revised_consensus.get("recommendations"):
            consensus = revised_consensus
            console.print(f"  -> {len(pushback_result.get('pushback', []))} objections raised and addressed")
            if pushback_result.get("overall_concern"):
                console.print(f"  -> Primary concern: {pushback_result['overall_concern'][:80]}...")
    except Exception as e:
        console.print(f"  [yellow]Pushback round failed ({e}), continuing with original consensus[/yellow]")

    # ── Step 12: Red team stress test ─────────────────────────────────────
    red_team_result = {}
    console.print(f"\n[bold cyan][11/12] Red team stress test...[/bold cyan]")
    try:
        from agents.red_team import run_red_team
        red_team_result = run_red_team(consensus, brief, quant_analysis=quant_analysis, output_dir=output_dir)
        critical = red_team_result.get("critical_count", 0)
        rating = red_team_result.get("overall_risk_rating", "unknown")
        console.print(f"  -> Risk rating: {rating} | {critical} critical issue(s)")
        if red_team_result.get("kill_recommendation"):
            console.print(f"  -> Weakest recommendation: {red_team_result.get('weakest_recommendation', '')[:60]}")
    except Exception as e:
        console.print(f"  [yellow]Red team failed ({e}), continuing without[/yellow]")

    # ── Step 13: Generate deliverables ────────────────────────────────────
    console.print("\n[bold cyan][12/12] Generating deliverables...[/bold cyan]")

    from deliverables.report_writer import write_report
    from deliverables.html_reporter import build_html_report
    from deliverables.chart_planner import plan_charts, extract_financial_text

    chart_plan = []
    try:
        financial_text = extract_financial_text(case_data)
        chart_plan = plan_charts(brief, financial_text, consensus, market_context=market_context)
        console.print(f"  -> Chart planner: {len(chart_plan)} visualizations planned")
    except Exception as e:
        console.print(f"  [yellow]Chart planning failed ({e}), continuing without charts[/yellow]")

    write_report(
        consensus, case_name, round1_results, output_dir,
        red_team=red_team_result,
        pushback=pushback_result,
        quant_analysis=quant_analysis,
        directions=directions,
        case_tags=case_tags,
    )
    html_path = build_html_report(
        consensus, case_name, round1_results, output_dir,
        red_team=red_team_result,
        pushback=pushback_result,
        quant_analysis=quant_analysis,
        directions=directions,
        case_tags=case_tags,
        chart_plan=chart_plan,
    )

    log_path = output_dir / f"{case_name}_agent_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"round1": round1_results, "round2": panel_results, "round3": consensus}, f, indent=2)
    console.print(f"  [green]Output:[/green] {log_path}")
    if html_path:
        console.print(f"  [green]HTML Report:[/green] {html_path}")

    # ── Step 8: Archive ───────────────────────────────────────────────────
    if not no_archive and not _interrupted:
        from archive import archive_case
        total_tokens = _estimate_tokens(len(personas), rounds)
        archive_case(
            case_name=case_name,
            active_dir=case_dir,
            output_dir=output_dir,
            consensus=consensus,
            n_agents=len(personas),
            n_rounds=rounds,
            question=question or "",
            total_tokens=total_tokens,
        )
    elif no_archive:
        console.print("\n[dim]Archive skipped (--no-archive)[/dim]")

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - start_total
    total_tokens = _estimate_tokens(len(personas), rounds)
    actual_cost = total_tokens / 1_000_000 * 3.0

    console.print()
    console.print(Rule())
    console.print(f"[green]Total cost: ~${actual_cost:.2f} ({total_tokens:,} tokens estimated)[/green]")
    console.print(f"[green]Total time: {int(elapsed // 60)}m {int(elapsed % 60)}s[/green]")
    console.print()


@app.command()
def learn(
    case_dir: Path = typer.Argument(..., help="Path to a past case directory"),
    industry: str = typer.Option(None, "--industry", help="Industry tag (e.g. nonprofit, healthcare)"),
    type_: str = typer.Option(None, "--type", help="Case type (e.g. revenue_diversification, turnaround)"),
):
    """Ingest a past case into the knowledge base."""
    _check_api_key()

    if not case_dir.exists() or not case_dir.is_dir():
        console.print(f"[red]Error: {case_dir} is not a valid directory[/red]")
        raise typer.Exit(1)

    console.print(Rule("[bold blue]Consulting Swarm — Learning[/bold blue]"))

    from knowledge.ingest_past_case import ingest_case
    try:
        num_chunks = ingest_case(case_dir, override_industry=industry, override_case_type=type_)
        console.print(f"\n[green]Ingested '{case_dir.name}' ({num_chunks} chunks)[/green]")
    except Exception as e:
        console.print(f"[red]Failed to ingest case: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def outcome(
    case_name: str = typer.Argument(..., help="Name of the past case (e.g. moa)"),
    outcome_text: str = typer.Argument(..., help="Outcome description to record"),
):
    """Record outcome data for a past case and re-embed it into the knowledge base."""
    console.print(Rule("[bold blue]Consulting Swarm — Outcome[/bold blue]"))
    from archive import add_outcome
    success = add_outcome(case_name, outcome_text)
    if not success:
        raise typer.Exit(1)

    # Update agent confidence scores
    try:
        from knowledge.confidence_tracker import update_from_outcome
        import json
        round1_path = Path("cases/past") / case_name / "output" / "round1_results.json"
        if not round1_path.exists():
            round1_path = Path("output") / case_name / "round1_results.json"
        if round1_path.exists():
            with open(round1_path, encoding="utf-8") as f:
                r1 = json.load(f)
            round1 = r1.get("results", r1) if isinstance(r1, dict) else r1
            tracker = update_from_outcome(case_name, outcome_text, round1)
            console.print(f"  -> Updated confidence scores for {len(tracker)} agents")
        else:
            console.print(f"  [dim]-> No round1 results found to update confidence scores[/dim]")
    except Exception as e:
        console.print(f"  [dim]-> Confidence tracker update skipped: {e}[/dim]")


@app.command(name="cases")
def list_cases():
    """List all cases and their status."""
    console.print(Rule("[bold blue]Consulting Swarm — Cases[/bold blue]"))

    active_dir = Path("cases/active")
    if active_dir.exists():
        active = [d for d in active_dir.iterdir() if d.is_dir()]
        console.print(f"\n[bold]Active Cases ({len(active)}):[/bold]")
        for case in sorted(active):
            has_brief = (case / "case_brief.md").exists()
            has_output = (Path("output") / case.name).exists()
            status = "analyzed" if has_output else ("brief ready" if has_brief else "materials only")
            console.print(f"  * {case.name} [{status}]")

    past_dir = Path("cases/past")
    if past_dir.exists():
        past = [d for d in past_dir.iterdir() if d.is_dir()]
        console.print(f"\n[bold]Past Cases — Archived ({len(past)}):[/bold]")
        for case in sorted(past):
            meta_path = case / "metadata.json"
            if meta_path.exists():
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                top = meta.get("top_recommendations", [])[:2]
                rec_str = f" | {'; '.join(top)}" if top else ""
                console.print(f"  * {case.name} [{meta.get('date_analyzed', '?')}]{rec_str}")
            else:
                console.print(f"  * {case.name}")

    from knowledge.vectorstore import list_cases as _list_kb
    try:
        kb_cases = _list_kb()
        console.print(f"\n[bold]Knowledge Base ({len(kb_cases)} cases indexed):[/bold]")
        for case in kb_cases:
            console.print(f"  * {case} [embedded]")
    except Exception:
        console.print("\n[dim]Knowledge base not initialized yet.[/dim]")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _check_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key == "your_key_here":
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Add it to .env[/red]")
        raise typer.Exit(1)


def _load_personas(max_agents: int) -> list:
    personas_path = Path(__file__).parent / "agents" / "personas.json"
    with open(personas_path, encoding="utf-8") as f:
        all_personas = json.load(f)
    return all_personas[:max_agents]


def _print_persona_breakdown(personas: list):
    from collections import Counter
    expertise_counts = Counter(exp for p in personas for exp in p.get("expertise", []))
    top = expertise_counts.most_common(6)
    summary = ", ".join(f"{count} {exp}" for exp, count in top)
    console.print(f"  -> Panel generated: {summary}")


def _estimate_cost(agents: int, rounds: int) -> float:
    r1 = agents * 2000 / 1_000_000 * 3.0
    r2 = (agents // 5) * 4000 / 1_000_000 * 3.0 if rounds >= 2 else 0
    r3 = 8000 / 1_000_000 * 3.0 if rounds >= 3 else 0
    extras = (
        4 * 8000 / 1_000_000 * 3.0    # quant extraction + pushback×2 + red team (Sonnet)
        + 2 * 2000 / 1_000_000 * 0.25  # selector + strategizer (Haiku)
    )
    return r1 + r2 + r3 + extras


def _estimate_tokens(agents: int, rounds: int) -> int:
    r1 = agents * 2000
    r2 = (agents // 5) * 4000 if rounds >= 2 else 0
    r3 = 8000 if rounds >= 3 else 0
    return r1 + r2 + r3


def _quick_consensus(round1_results: list) -> dict:
    """Minimal fallback consensus from Round 1 only."""
    from collections import Counter
    all_recs = [r for a in round1_results for r in a.get("analysis", {}).get("recommendations", [])]
    all_problems = [p for a in round1_results for p in a.get("analysis", {}).get("key_problems", [])]
    title_counts = Counter(r.get("title", "") for r in all_recs if r.get("title"))
    top_titles = [t for t, _ in title_counts.most_common(5)]

    top_recs = []
    seen = set()
    for title in top_titles:
        for rec in all_recs:
            if rec.get("title") == title and title not in seen:
                top_recs.append({**rec, "rank": len(top_recs) + 1, "panel_support": f"{title_counts[title]}/{len(round1_results)} agents"})
                seen.add(title)
                break

    key_insights = [a.get("analysis", {}).get("key_insight", "") for a in round1_results if a.get("analysis", {}).get("key_insight")]
    return {
        "executive_summary": f"Analysis by {len(round1_results)} consultants identified {len(top_recs)} key recommendations.",
        "problem_statement": all_problems[0] if all_problems else "See key findings.",
        "analysis_framework": "Multi-expert independent analysis",
        "key_findings": [{"finding": p, "evidence": "", "confidence": 0.7} for p in set(all_problems[:4])],
        "recommendations": top_recs,
        "risk_assessment": "See full agent log for risk assessments.",
        "minority_views": [],
        "implementation_roadmap": {"phase_1_0_3_months": [], "phase_2_3_6_months": [], "phase_3_6_12_months": []},
        "missing_information": [],
        "bottom_line": key_insights[0] if key_insights else "See recommendations.",
    }


def _save_partial(output_dir: Path, **kwargs):
    output_dir.mkdir(parents=True, exist_ok=True)
    partial_path = output_dir / "partial_results.json"
    with open(partial_path, "w", encoding="utf-8") as f:
        json.dump(kwargs, f, indent=2, default=str)
    console.print(f"[yellow]Partial results saved to {partial_path}[/yellow]")


if __name__ == "__main__":
    app()
