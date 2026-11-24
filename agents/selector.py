"""
Dynamic panel selector — picks the most relevant agents for a given case brief.
Uses one cheap Haiku call to extract case tags, then scores personas by tag overlap.
Cost: ~$0.001 per analysis.
"""

import json
import os

import httpx

SELECTOR_PROMPT = """Read this consulting case brief carefully. Return a JSON list of 5-8 tags describing the key industries, challenges, and expertise areas most relevant to this case.

Examples: ["nonprofit", "revenue_diversification", "membership", "facility_management", "marketing"]

Respond ONLY with the JSON array — no other text, no markdown fences.

Case brief:
{brief}"""

DOMAIN_KEYWORDS = {
    "museum": ["museum", "gallery", "exhibit", "artifact", "curator", "collection", "cultural institution", "aquarium", "zoo"],
    "nonprofit": ["nonprofit", "mission", "donor", "grant", "501c", "charitable", "foundation", "ngo"],
    "membership": ["membership", "member", "subscriber", "dues", "annual pass", "renew"],
    "healthcare": ["hospital", "clinic", "patient", "healthcare", "medical", "health system", "fqhc"],
    "saas": ["saas", "software as a service", "arr", "mrr", "churn rate", "recurring revenue"],
    "retail": ["retail", "store", "inventory", "merchandise", "shop", "gift shop", "point of sale"],
    "ecommerce": ["ecommerce", "e-commerce", "online store", "dtc", "direct to consumer", "shopify"],
    "education": ["school", "university", "student", "curriculum", "education", "learning", "academic"],
    "government": ["government", "public sector", "regulatory", "policy", "municipal", "federal", "grant"],
    "real_estate": ["real estate", "property", "lease", "facility", "building", "space", "sublease"],
    "fundraising": ["fundraising", "development", "campaign", "donation", "philanthropy", "major gift"],
    "sustainability": ["sustainability", "climate", "esg", "carbon", "environmental", "green", "net zero"],
    "marketing": ["marketing", "brand", "advertising", "customer acquisition", "retention", "awareness"],
    "technology": ["technology", "digital", "software", "platform", "data", "automation", "crm", "app"],
    "finance": ["revenue", "cost reduction", "profit", "cash flow", "budget", "financial", "deficit"],
    "operations": ["operations", "process", "efficiency", "capacity", "workflow", "staffing", "throughput"],
    "franchise": ["franchise", "licensing", "affiliate", "branch", "network", "replication"],
    "pricing": ["pricing", "price", "willingness to pay", "tiered", "premium", "value proposition"],
    "supply_chain": ["supply chain", "procurement", "vendor", "inventory", "logistics", "sourcing"],
    "community": ["community", "volunteer", "engagement", "grassroots", "constituency", "outreach"],
}


def select_panel(case_brief: str, all_personas: list, n_agents: int = 20) -> tuple:
    """
    Select the most relevant agents for a case.
    Returns: (selected_personas, case_tags)
    """
    case_tags = _extract_case_tags(case_brief)
    scored = _score_personas(all_personas, case_tags)
    selected = _apply_diversity(scored, n_agents)
    return selected, case_tags


def _extract_case_tags(case_brief: str) -> list:
    """Make one Haiku call to extract case tags. Falls back to keyword matching."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": SELECTOR_PROMPT.format(brief=case_brief[:3000])}],
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            text = response.json()["content"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            tags = json.loads(text)
            if isinstance(tags, list):
                return [str(t).lower() for t in tags]
    except Exception:
        pass
    return _fallback_tags(case_brief)


def _fallback_tags(brief: str) -> list:
    brief_lower = brief.lower()
    tags = [tag for tag, keywords in DOMAIN_KEYWORDS.items()
            if any(kw in brief_lower for kw in keywords)]
    return tags[:8] if tags else ["strategy", "operations", "finance"]


def _score_personas(all_personas: list, case_tags: list) -> list:
    """Score each persona by tag overlap with case tags."""
    case_tag_set = set(t.lower() for t in case_tags)
    scored = []
    for persona in all_personas:
        persona_tags = set(t.lower() for t in persona.get("tags", []))
        expertise_tags = set(t.lower() for t in persona.get("expertise", []))
        overlap = len((persona_tags | expertise_tags) & case_tag_set)
        scored.append((overlap, persona))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _apply_diversity(scored: list, n_agents: int) -> list:
    """
    Select agents with diversity constraints:
    - No more than 3 agents from same primary expertise
    - Must include at least 1 contrarian
    - Must include at least 1 finance specialist
    - Must include at least 1 operations specialist
    """
    selected = []
    expertise_counts = {}
    selected_ids = set()

    for _, persona in scored:
        if len(selected) >= n_agents:
            break
        pid = persona.get("id")
        if pid in selected_ids:
            continue
        primary_exp = persona.get("expertise", ["general"])[0]
        if expertise_counts.get(primary_exp, 0) >= 3:
            continue
        selected.append(persona)
        selected_ids.add(pid)
        expertise_counts[primary_exp] = expertise_counts.get(primary_exp, 0) + 1

    # Ensure required specialists are present
    required = [
        ("contrarian", "thinking_style"),
        ("finance", "expertise"),
        ("operations", "expertise"),
    ]
    for req_val, req_field in required:
        has_it = any(
            (req_val in p.get(req_field, []) if isinstance(p.get(req_field), list)
             else req_val in p.get(req_field, ""))
            for p in selected
        )
        if not has_it:
            for _, persona in scored:
                if persona.get("id") in selected_ids:
                    continue
                val = persona.get(req_field, [])
                match = (req_val in val) if isinstance(val, list) else (req_val in val)
                if match:
                    if len(selected) >= n_agents:
                        removed = selected.pop()
                        selected_ids.discard(removed.get("id"))
                    selected.append(persona)
                    selected_ids.add(persona.get("id"))
                    break

    return selected[:n_agents]
