"""Round 3 — Consensus building. Synthesizes all panel outputs into final analysis."""

import json
import logging
import os
import time
from pathlib import Path

import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console(file=sys.stdout)

CONSENSUS_SYSTEM = """You are the senior partner synthesizing the findings from consulting panels who analyzed a business case. Each panel had 5 diverse consultants who deliberated independently.

Your job is to produce the definitive analysis:
1. Identify the 3-5 strongest recommendations (broadest support and strongest evidence)
2. Rank them by impact × feasibility
3. Build a clear narrative: problem → analysis → recommendations → implementation
4. Preserve important minority views — if multiple panels raised a concern, it matters
5. Be decisive. The client needs clear direction, not "on one hand / on the other hand."

Respond ONLY with valid JSON in this exact structure (no markdown fences, no extra text):
{
  "executive_summary": "3-4 sentence overview for a busy executive",
  "problem_statement": "clear articulation of the core problem",
  "analysis_framework": "what analytical lenses were applied",
  "key_findings": [
    {"finding": "...", "evidence": "...", "confidence": 0.9}
  ],
  "recommendations": [
    {
      "rank": 1,
      "title": "...",
      "description": "...",
      "rationale": "why this is the top priority",
      "implementation_steps": ["step 1", "step 2", "step 3"],
      "timeline": "...",
      "expected_impact": "...",
      "risks_and_mitigations": "...",
      "panel_support": "8/10 panels endorsed this",
      "cost_estimate": "if applicable"
    }
  ],
  "risk_assessment": "top 3-5 risks to the overall strategy",
  "minority_views": [
    {"view": "...", "raised_by": "N/10 panels", "merit": "why this deserves consideration"}
  ],
  "implementation_roadmap": {
    "phase_1_0_3_months": ["..."],
    "phase_2_3_6_months": ["..."],
    "phase_3_6_12_months": ["..."]
  },
  "missing_information": ["what the client should investigate further"],
  "bottom_line": "the single most important thing the client should do"
}"""


def run_round3(
    panel_results: list,
    case_name: str = "case",
    output_dir: Path = Path("output"),
) -> dict:
    """
    Single synthesis call that reviews all panel outputs and produces final consensus.
    Returns the consensus dict.
    """
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()

    console.print(f"\n[bold cyan][6/8] Round 3 — Consensus Building...[/bold cyan]")
    start = time.time()

    # Build input from all panel results
    panel_sections = []
    for panel in panel_results:
        panel_num = panel.get("panel_num", "?")
        agents = panel.get("agents", [])
        result = panel.get("result", {})
        section = f"""## Panel {panel_num} ({', '.join(agents[:3])}...)
Consensus Recommendations: {json.dumps(result.get('consensus_recommendations', [])[:3], indent=2)}
Key Agreements: {json.dumps(result.get('key_agreements', []))}
Key Disagreements: {json.dumps(result.get('key_disagreements', []))}
Strongest Dissent: {result.get('strongest_dissent', 'N/A')}
Confidence: {result.get('confidence_level', 'N/A')}"""
        panel_sections.append(section)

    user_content = "\n\n".join(panel_sections)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=CONSENSUS_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    text = response.content[0].text
    consensus = _parse_json(text)

    # Print summary stats
    recs = consensus.get("recommendations", [])
    minority = consensus.get("minority_views", [])
    console.print(f"  → Final {len(recs)} recommendations selected")
    if minority:
        console.print(f"  → Dissent report: {len(minority)} significant minority view(s) captured")

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "round3_consensus.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "consensus": consensus,
            "case_name": case_name,
            "elapsed_seconds": time.time() - start,
        }, f, indent=2)

    return consensus


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
        logger.error(f"Failed to parse consensus JSON: {text[:200]}")
        return {"parse_error": True, "raw": text[:500], "executive_summary": "Consensus generation failed — see raw output."}
