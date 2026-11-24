"""
Round 3.5 — Simulates a skeptical client pushing back on consensus recommendations,
then has the senior partner revise the consensus to address those objections.
Two Sonnet calls. Cost: ~$0.02.
"""

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PUSHBACK_SYSTEM = """You are the client — the CEO or Executive Director who has run this organization for years. You have seen consultants come and go. You are reading the final recommendations from a consulting team.

Push back with specific, realistic objections a real experienced leader would raise:
- Things you've tried before that failed and why
- What the board will or won't approve without more evidence
- Staff capacity and bandwidth realities
- Seasonal or operational constraints
- Financial risk tolerance
- What's missing from the analysis

For each recommendation, give 1-2 specific objections and state what would need to be true for you to approve it.

Respond ONLY with this JSON (no markdown fences):
{
  "pushback": [
    {
      "recommendation": "recommendation title",
      "objections": ["specific objection 1", "specific objection 2"],
      "conditions_for_buy_in": "what would need to be true to approve this"
    }
  ],
  "overall_concern": "the single biggest thing worrying you about this plan",
  "missing": "what the consultants didn't address that you need answered"
}"""

REVISION_SYSTEM = """You are the senior partner who produced the original consensus recommendations. Your client has pushed back with specific objections.

Revise your recommendations to address each objection:
- Defend solid recommendations — don't abandon them just because the client pushed back
- Acknowledge legitimate concerns and add implementation safeguards
- Add milestones, contingency plans, and conditions that address the client's buy-in requirements
- Where the client raised something genuinely missed, incorporate it

Return a revised version of the consensus JSON with the same structure, but with enhanced implementation_steps and risks_and_mitigations per recommendation. Also add a top-level "client_considerations" field (string) summarizing how you addressed each major objection.

Respond ONLY with valid JSON (no markdown fences). Same structure as input."""


def run_pushback_round(
    consensus: dict,
    case_brief: str,
    output_dir: Path = Path("output"),
) -> tuple:
    """
    Run client pushback + senior partner revision.
    Returns: (pushback_result, revised_consensus)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    pushback = _client_pushback(api_key, consensus, case_brief)
    revised = _senior_revision(api_key, consensus, pushback)

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "pushback.json", "w", encoding="utf-8") as f:
        json.dump({"pushback": pushback, "revised_consensus": revised}, f, indent=2)

    return pushback, revised


def _client_pushback(api_key: str, consensus: dict, case_brief: str) -> dict:
    recs_summary = json.dumps([
        {"title": r.get("title"), "description": r.get("description"), "timeline": r.get("timeline")}
        for r in consensus.get("recommendations", [])
    ], indent=2)
    user = f"## Our Recommendations\n{recs_summary}\n\n## Original Case Context\n{case_brief[:2000]}"
    return _call(api_key, PUSHBACK_SYSTEM, user, max_tokens=1500)


def _senior_revision(api_key: str, original: dict, pushback: dict) -> dict:
    user = (
        f"## Original Consensus\n{json.dumps(original, indent=2)[:4000]}\n\n"
        f"## Client Pushback\n{json.dumps(pushback, indent=2)[:2000]}"
    )
    result = _call(api_key, REVISION_SYSTEM, user, max_tokens=2500)
    if result.get("parse_error") or not result.get("recommendations"):
        # Fallback: return original with pushback appended
        original["client_considerations"] = pushback.get("overall_concern", "")
        original["_pushback"] = pushback
        return original
    return result


def _call(api_key: str, system: str, user: str, max_tokens: int = 1500) -> dict:
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        with httpx.Client(timeout=90.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return json.loads(text)
    except Exception as e:
        logger.error(f"Pushback call failed: {e}")
        return {"parse_error": True, "error": str(e)}
