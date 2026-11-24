"""Find relevant past cases for a new analysis."""

import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def retrieve_past_cases(case_brief: str, top_n: int = 3, tokens_per_case: int = 600) -> str:
    """
    Find the top N most relevant past cases for a given case brief.
    Returns a formatted string ready for inclusion in agent prompts.
    """
    try:
        from knowledge.vectorstore import query_similar, list_cases
    except ImportError as e:
        logger.warning(f"Knowledge base not available: {e}")
        return "No past cases available."

    try:
        known_cases = list_cases()
        if not known_cases:
            return "No past cases in knowledge base."

        # Embed the case brief and query
        results = query_similar(case_brief[:2000], n_results=25)

        if not results:
            return "No relevant past cases found."

        # Group by case_name and rank by aggregate similarity
        case_scores = defaultdict(list)
        case_chunks = defaultdict(list)

        for result in results:
            meta = result.get("metadata", {})
            case_name = meta.get("case_name", "Unknown")
            # ChromaDB cosine distance: lower = more similar
            score = 1.0 - result.get("distance", 1.0)
            case_scores[case_name].append(score)
            case_chunks[case_name].append(result)

        # Aggregate: average similarity
        case_avg = {name: sum(scores) / len(scores) for name, scores in case_scores.items()}
        top_cases = sorted(case_avg.items(), key=lambda x: -x[1])[:top_n]

        if not top_cases:
            return "No relevant past cases found."

        # Format output
        parts = [f"## Relevant Past Cases ({len(top_cases)} found)\n"]
        for case_name, avg_score in top_cases:
            chunks = sorted(case_chunks[case_name], key=lambda x: x.get("distance", 1.0))
            industry = chunks[0].get("metadata", {}).get("industry", "unknown") if chunks else "unknown"
            case_type = chunks[0].get("metadata", {}).get("case_type", "unknown") if chunks else "unknown"

            parts.append(f"### {case_name} (similarity: {avg_score:.2f})")
            parts.append(f"*Industry: {industry} | Type: {case_type}*\n")

            # Include the most relevant chunks, up to token budget
            char_budget = tokens_per_case * 4  # rough chars per token
            for chunk in chunks[:4]:
                text = chunk.get("text", "")[:char_budget // 2]
                parts.append(text)
                char_budget -= len(text)
                if char_budget <= 0:
                    break
            parts.append("")

        return "\n".join(parts)

    except Exception as e:
        logger.error(f"Failed to retrieve past cases: {e}", exc_info=True)
        return f"Past case retrieval failed: {e}"
