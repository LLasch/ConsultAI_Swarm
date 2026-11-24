"""
Agent confidence tracking across analyses.
Tracks prediction accuracy over time and computes weight multipliers.
Zero API calls — pure Python.
"""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

TRACKER_PATH = Path(__file__).parent / "confidence_tracker.json"


def load_tracker() -> dict:
    if TRACKER_PATH.exists():
        try:
            with open(TRACKER_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load confidence tracker: {e}")
    return {}


def save_tracker(tracker: dict):
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_PATH, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)


def get_agent_weights(personas: list) -> dict:
    """
    Returns dict of str(agent_id) -> weight_multiplier.
    New agents: 1.0 (neutral).
    Tracked agents: 0.5 (always wrong) to 1.5 (always right).
    """
    tracker = load_tracker()
    weights = {}
    for persona in personas:
        agent_id = str(persona.get("id", ""))
        avg_accuracy = tracker.get(agent_id, {}).get("average_accuracy", None)
        weights[agent_id] = round(0.5 + avg_accuracy, 3) if avg_accuracy is not None else 1.0
    return weights


def update_from_outcome(case_name: str, outcome_text: str, round1_results: list) -> dict:
    """
    Update agent accuracy scores based on a case outcome.
    Called when `python main.py outcome <case_name> "..."` is run.

    Scoring:
      1.0 — agent was positive, outcome was positive
      0.5 — outcome was mixed/uncertain
      0.0 — outcome was clearly negative
    """
    tracker = load_tracker()
    outcome_lower = outcome_text.lower()

    positive = ["success", "exceeded", "grew", "increased", "improved", "launched", "achieved", "positive", "strong"]
    negative = ["failed", "struggled", "declined", "worse", "unsuccessful", "dropped", "negative", "poor"]
    mixed = ["mixed", "partial", "modest", "limited", "moderate", "some progress"]

    pos = sum(1 for w in positive if w in outcome_lower)
    neg = sum(1 for w in negative if w in outcome_lower)

    if pos > neg:
        outcome_quality = 1.0
    elif neg > pos:
        outcome_quality = 0.0
    elif any(w in outcome_lower for w in mixed):
        outcome_quality = 0.5
    else:
        outcome_quality = 0.7  # neutral/unknown

    for agent in round1_results:
        agent_id = str(agent.get("id", ""))
        if not agent_id:
            continue

        recs = agent.get("analysis", {}).get("recommendations", [])
        if agent_id not in tracker:
            tracker[agent_id] = {
                "name": agent.get("name", "Unknown"),
                "cases_analyzed": 0,
                "predictions": [],
                "average_accuracy": None,
                "weight_multiplier": 1.0,
            }

        data = tracker[agent_id]
        data["cases_analyzed"] = data.get("cases_analyzed", 0) + 1
        data["predictions"].append({
            "case": case_name,
            "top_recommendation": recs[0].get("title", "") if recs else "",
            "n_recommendations": len(recs),
            "outcome_quality": outcome_quality,
            "date": date.today().isoformat(),
        })

        scores = [p["outcome_quality"] for p in data["predictions"]]
        data["average_accuracy"] = round(sum(scores) / len(scores), 3)
        data["weight_multiplier"] = round(0.5 + data["average_accuracy"], 3)
        tracker[agent_id] = data

    save_tracker(tracker)
    return tracker
