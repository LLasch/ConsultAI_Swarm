"""
regen_charts.py — Regenerate the HTML report for an existing case using the new chart planner.

Usage:
    py regen_charts.py "cases/past/Museum of Archeology"
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


def main():
    case_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cases/past/Museum of Archeology")
    output_dir = case_dir / "output"
    case_name = case_dir.name

    print(f"[regen] Case: {case_name}")
    print(f"[regen] Output dir: {output_dir}")

    # Load existing consensus
    consensus_path = output_dir / "round3_consensus.json"
    if not consensus_path.exists():
        print("[regen] No round3_consensus.json found — cannot proceed")
        sys.exit(1)

    consensus_raw = json.loads(consensus_path.read_text(encoding="utf-8"))
    consensus = consensus_raw.get("consensus", consensus_raw)

    # Load round1 results for agent count
    round1_path = output_dir / "round1_results.json"
    round1_results = []
    if round1_path.exists():
        data = json.loads(round1_path.read_text(encoding="utf-8"))
        round1_results = data if isinstance(data, list) else []

    # Load case brief
    brief_path = case_dir / "materials" / "case_brief.md"
    brief = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""

    # Extract financial text from spreadsheets
    financial_text = ""
    for f in (case_dir / "materials").rglob("*"):
        if f.suffix.lower() in (".csv", ".txt") and f.is_file():
            try:
                financial_text += f.read_text(encoding="utf-8", errors="ignore")[:1500]
            except Exception:
                pass

    print(f"[regen] Brief: {len(brief)} chars | Financial text: {len(financial_text)} chars")
    print(f"[regen] Round1 agents: {len(round1_results)}")

    # Step 1: Chart planning
    print("[regen] Running chart planner...")
    from deliverables.chart_planner import plan_charts
    chart_plan = plan_charts(brief, financial_text, consensus)
    print(f"[regen] Chart plan: {len(chart_plan)} specs")
    for s in chart_plan:
        print(f"  - [{s.get('chart_type','?')}] {s.get('title','?')[:60]}  -> {s.get('placement','?')}")

    # Step 2: Regenerate HTML report
    print("[regen] Building HTML report...")
    from deliverables.html_reporter import build_html_report
    out_path = build_html_report(
        consensus=consensus,
        case_name=case_name,
        round1_results=round1_results,
        output_dir=output_dir,
        chart_plan=chart_plan,
    )

    if out_path:
        print(f"\n[regen] Done! Report written to:\n  {out_path}")
    else:
        print("[regen] HTML report generation failed — check logs above")


if __name__ == "__main__":
    main()
