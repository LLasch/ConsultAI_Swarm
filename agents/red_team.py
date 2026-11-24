"""
Post-consensus adversarial red team stress test.
One Sonnet call. Cost: ~$0.01.
"""

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

RED_TEAM_SYSTEM = """You are a panel of 3 adversarial analysts whose job is to stress-test these consulting recommendations. Find the weaknesses. Look for:

1. LOGICAL FLAWS — Does the reasoning actually follow? Circular arguments?
2. MISSING EVIDENCE — Which claims are unsupported by case data?
3. UNREALISTIC ASSUMPTIONS — Which numbers seem optimistic or made up?
4. IMPLEMENTATION RISKS — What could go wrong in execution that wasn't considered?
5. SECOND-ORDER EFFECTS — What unintended consequences might these create?
6. STAKEHOLDER REACTION — How will competitors, staff, donors, or community react?
7. WORST CASE — If everything goes wrong, what's the downside?

Be ruthless. If a recommendation is strong, say so — but find the weakest points in even the strongest ones.

Respond ONLY with this JSON (no markdown fences):
{
  "vulnerabilities": [
    {
      "recommendation": "title",
      "severity": "critical|high|medium|low",
      "vulnerability": "specific weakness description",
      "mitigation_suggestion": "how to address this"
    }
  ],
  "overall_risk_rating": "low|medium|high",
  "strongest_recommendation": "which one survives scrutiny best and why",
  "weakest_recommendation": "which one has the most holes and why",
  "kill_recommendation": "if you had to cut ONE recommendation entirely, which and why"
}"""


def run_red_team(
    consensus: dict,
    case_brief: str,
    quant_analysis: dict = None,
    output_dir: Path = Path("output"),
) -> dict:
    """
    Run adversarial red team analysis.
    Returns vulnerabilities dict.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    recs_text = json.dumps(consensus.get("recommendations", []), indent=2)[:3000]
    user_parts = [
        f"## Recommendations Under Review\n{recs_text}",
        f"\n## Case Context\n{case_brief[:1500]}",
    ]
    if quant_analysis and quant_analysis.get("summary"):
        user_parts.append(f"\n## Financial Analysis\n{quant_analysis['summary']}")

    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": RED_TEAM_SYSTEM,
            "messages": [{"role": "user", "content": "\n".join(user_parts)}],
        }
        with httpx.Client(timeout=90.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(text)
    except Exception as e:
        logger.error(f"Red team call failed: {e}")
        result = {"parse_error": True, "error": str(e), "vulnerabilities": []}

    result["critical_count"] = len([v for v in result.get("vulnerabilities", []) if v.get("severity") == "critical"])

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "red_team.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result
