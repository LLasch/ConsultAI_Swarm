"""Parse interview transcripts and extract key quotes and themes."""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns for speaker attribution
SPEAKER_PATTERNS = [
    r"^([A-Z][a-zA-Z\s\.]+):\s*(.+)",        # "John Smith: ..."
    r"^\*\*([A-Z][a-zA-Z\s\.]+)\*\*:\s*(.+)", # "**John Smith**: ..."
    r"^(Q|A|Interviewer|Respondent):\s*(.+)",  # "Q: ..." / "A: ..."
    r"^\[([A-Z][a-zA-Z\s]+)\]:\s*(.+)",        # "[Speaker]: ..."
]

COMPILED_PATTERNS = [re.compile(p, re.MULTILINE) for p in SPEAKER_PATTERNS]


def parse_transcript(text: str, filename: str = "") -> dict:
    """
    Parse a transcript text into speakers, quotes, and themes.
    Returns structured dict with speaker_map and key_quotes.
    """
    speaker_map: dict[str, list[str]] = {}
    all_statements = []

    lines = text.split("\n")
    current_speaker = None
    current_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        matched = False
        for pattern in COMPILED_PATTERNS:
            m = pattern.match(line)
            if m:
                # Save previous speaker's block
                if current_speaker and current_lines:
                    statement = " ".join(current_lines)
                    speaker_map.setdefault(current_speaker, []).append(statement)
                    all_statements.append({"speaker": current_speaker, "text": statement})

                current_speaker = m.group(1).strip()
                current_lines = [m.group(2).strip()] if m.group(2).strip() else []
                matched = True
                break

        if not matched and current_speaker:
            current_lines.append(line)

    # Flush last speaker
    if current_speaker and current_lines:
        statement = " ".join(current_lines)
        speaker_map.setdefault(current_speaker, []).append(statement)
        all_statements.append({"speaker": current_speaker, "text": statement})

    # If no speakers detected, treat whole text as unstructured
    if not speaker_map:
        return {
            "type": "interview_unstructured",
            "filename": filename,
            "speakers": [],
            "key_quotes": _extract_key_quotes_unstructured(text),
            "text": text,
        }

    key_quotes = _extract_key_quotes(speaker_map)
    themes = _identify_themes(all_statements)

    parts = []
    parts.append(f"**Speakers:** {', '.join(speaker_map.keys())}")
    parts.append(f"**Total exchanges:** {len(all_statements)}")
    parts.append("\n**Key Quotes by Speaker:**")
    for speaker, quotes in key_quotes.items():
        parts.append(f"\n*{speaker}:*")
        for q in quotes[:3]:
            parts.append(f'  > "{q}"')
    if themes:
        parts.append("\n**Recurring Themes:**")
        for t in themes:
            parts.append(f"  - {t}")

    return {
        "type": "interview",
        "filename": filename,
        "speakers": list(speaker_map.keys()),
        "speaker_map": {k: v[:5] for k, v in speaker_map.items()},  # cap per speaker
        "key_quotes": key_quotes,
        "themes": themes,
        "text": "\n".join(parts),
    }


def _extract_key_quotes(speaker_map: dict) -> dict:
    """Pick the most substantive quotes (longest, most informative) per speaker."""
    result = {}
    for speaker, statements in speaker_map.items():
        # Sort by length, skip very short ones
        substantive = [s for s in statements if len(s) > 40]
        substantive.sort(key=len, reverse=True)
        result[speaker] = substantive[:3]
    return result


def _extract_key_quotes_unstructured(text: str) -> list:
    """For unstructured text, extract sentences containing key signal words."""
    sentences = re.split(r"[.!?]+", text)
    signal_words = ["challenge", "problem", "opportunity", "concern", "recommend", "believe", "important", "critical", "need", "should", "must", "revenue", "growth", "risk"]
    key = []
    for s in sentences:
        s = s.strip()
        if len(s) > 40 and any(w in s.lower() for w in signal_words):
            key.append(s)
    return key[:10]


def _identify_themes(statements: list) -> list:
    """Simple keyword-frequency based theme detection."""
    theme_keywords = {
        "revenue / funding": ["revenue", "funding", "money", "budget", "financial", "income", "donation", "grant"],
        "membership": ["member", "membership", "subscriber", "retention", "churn"],
        "operations": ["operations", "process", "efficiency", "staff", "capacity", "resources"],
        "growth / strategy": ["grow", "growth", "expand", "strategy", "opportunity", "market"],
        "technology": ["technology", "digital", "software", "system", "platform", "data"],
        "culture / change": ["culture", "change", "team", "leadership", "morale", "communication"],
        "customers / beneficiaries": ["customer", "client", "beneficiary", "community", "user", "participant"],
        "risk / concern": ["risk", "concern", "challenge", "problem", "issue", "threat"],
    }

    text_lower = " ".join(s["text"].lower() for s in statements)
    found = []
    for theme, keywords in theme_keywords.items():
        count = sum(text_lower.count(kw) for kw in keywords)
        if count >= 2:
            found.append((theme, count))

    found.sort(key=lambda x: -x[1])
    return [f[0] for f in found[:5]]
