"""
Generates 4 competing strategic directions for a case, then assigns agent teams.
Uses one Haiku call.
Cost: ~$0.001
"""

import json
import os

import httpx

DIRECTIONS_PROMPT = """Given this business case brief, identify 4 fundamentally different strategic directions the organization could pursue. They should be genuinely distinct approaches — not variations of the same idea.

Think along lines like: organic revenue growth vs cost transformation vs strategic partnerships vs mission refocus. The right 4 directions depend on the specific case.

Return ONLY this JSON array (no markdown fences, no other text):
[
  {{"direction": "short name (2-4 words)", "description": "one sentence describing this strategic path"}},
  {{"direction": "short name", "description": "one sentence"}},
  {{"direction": "short name", "description": "one sentence"}},
  {{"direction": "short name", "description": "one sentence"}}
]

Case brief:
{brief}"""

FALLBACK_DIRECTIONS = [
    {"direction": "Revenue Expansion", "description": "Aggressively grow earned revenue through new products, services, and markets."},
    {"direction": "Cost Transformation", "description": "Restructure cost base while protecting core mission, achieving profitability through efficiency."},
    {"direction": "Strategic Partnerships", "description": "Grow through alliances, mergers, or partnerships that multiply capacity without proportional investment."},
    {"direction": "Mission Refocus", "description": "Narrow scope to highest-impact, most financially sustainable programs and double down on excellence."},
]


def generate_strategic_directions(case_brief: str) -> list:
    """
    Generate 4 competing strategic directions via Haiku.
    Returns list of {"direction": str, "description": str} dicts.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": DIRECTIONS_PROMPT.format(brief=case_brief[:3000])}],
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            directions = json.loads(text)
            if isinstance(directions, list) and len(directions) >= 4:
                return [{"direction": d["direction"], "description": d["description"]} for d in directions[:4]]
    except Exception:
        pass
    return FALLBACK_DIRECTIONS


def assign_teams(personas: list, directions: list) -> list:
    """
    Assign agents to direction teams, ensuring expertise diversity within each team.
    Returns list of team dicts: {"direction": str, "description": str, "agents": list}
    """
    n_teams = len(directions)
    if n_teams == 0 or not personas:
        return []

    # Interleave by expertise to ensure diverse teams
    expertise_groups: dict = {}
    for p in personas:
        exp = p.get("expertise", ["general"])[0]
        expertise_groups.setdefault(exp, []).append(p)

    ordered = []
    max_len = max(len(g) for g in expertise_groups.values())
    for i in range(max_len):
        for group in expertise_groups.values():
            if i < len(group):
                ordered.append(group[i])

    # Distribute round-robin across teams
    teams = [{"direction": d["direction"], "description": d["description"], "agents": []}
             for d in directions]
    for i, persona in enumerate(ordered):
        teams[i % n_teams]["agents"].append(persona)

    return teams
