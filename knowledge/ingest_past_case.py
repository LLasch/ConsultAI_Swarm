"""Process and embed a completed past case into the knowledge base."""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional

import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console(file=sys.stdout)


def ingest_case(case_dir: Path, override_industry: str = None, override_case_type: str = None) -> int:
    """
    Ingest a past case directory into the knowledge base.
    Returns number of chunks stored.
    """
    from ingestion.case_loader import load_case
    from knowledge.vectorstore import store_chunks

    console.print(f"\n[bold cyan]Ingesting past case: {case_dir.name}[/bold cyan]")

    # Load case materials
    case_data = load_case(case_dir, console=console)
    brief = case_data["brief"]
    case_name = case_data["case_name"]

    # Check for existing deliverables (report, recommendations)
    existing_report = _find_existing_report(case_dir)
    outcome_data = _find_outcome(case_dir)

    # Chunk content into meaningful segments
    chunks = []

    # Chunk 1: Case brief (split by section)
    brief_chunks = _chunk_by_section(brief, case_name, "brief")
    chunks.extend(brief_chunks)

    # Chunk 2: Existing report
    if existing_report:
        report_chunks = _chunk_by_section(existing_report, case_name, "report")
        chunks.extend(report_chunks)

    # Chunk 3: Outcome data
    if outcome_data:
        outcome_chunk = {
            "id": _make_id(case_name, "outcome", 0),
            "text": f"OUTCOME for {case_name}:\n{outcome_data[:3000]}",
            "metadata": {
                "case_name": case_name,
                "chunk_type": "outcome",
                "case_dir": str(case_dir),
            },
        }
        chunks.append(outcome_chunk)

    # Infer metadata (overrides take priority)
    industry = override_industry or _detect_industry(brief)
    case_type = override_case_type or _detect_case_type(brief)

    for chunk in chunks:
        chunk["metadata"]["industry"] = industry
        chunk["metadata"]["case_type"] = case_type

    store_chunks(chunks)
    console.print(f"  ✓ Stored {len(chunks)} chunks for '{case_name}'")
    return len(chunks)


def _chunk_by_section(text: str, case_name: str, chunk_type: str) -> list[dict]:
    """Split text by markdown headers into meaningful sections."""
    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 50:
            continue
        # Truncate very long sections
        if len(section) > 3000:
            section = section[:3000] + "..."
        chunks.append({
            "id": _make_id(case_name, chunk_type, i),
            "text": section,
            "metadata": {
                "case_name": case_name,
                "chunk_type": chunk_type,
                "section_index": i,
            },
        })
    return chunks


def _make_id(case_name: str, chunk_type: str, idx: int) -> str:
    raw = f"{case_name}_{chunk_type}_{idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def _find_existing_report(case_dir: Path) -> Optional[str]:
    """Look for an existing report file in the case directory."""
    for pattern in ["*_report.md", "report.md", "*.md", "*report*.txt"]:
        matches = list(case_dir.glob(pattern))
        for match in matches:
            if match.name != "case_brief.md" and match.stat().st_size > 500:
                try:
                    return match.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
    return None


def _find_outcome(case_dir: Path) -> Optional[str]:
    """Look for outcome or results files."""
    for pattern in ["outcome*.txt", "outcome*.md", "results*.md", "results*.txt", "followup*.md"]:
        matches = list(case_dir.glob(pattern))
        for match in matches:
            try:
                return match.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return None


def _detect_industry(text: str) -> str:
    text_lower = text.lower()
    industry_keywords = {
        "nonprofit": ["nonprofit", "non-profit", "charity", "foundation", "501c", "ngo", "mission"],
        "healthcare": ["hospital", "clinic", "healthcare", "medical", "health system", "patient"],
        "education": ["school", "university", "college", "education", "student", "academic"],
        "retail": ["retail", "store", "ecommerce", "consumer goods", "merchandise"],
        "technology": ["software", "saas", "technology", "startup", "platform", "digital"],
        "finance": ["bank", "financial services", "insurance", "investment", "fintech"],
        "manufacturing": ["manufacturing", "factory", "production", "supply chain", "industrial"],
    }
    scores = {}
    for industry, keywords in industry_keywords.items():
        scores[industry] = sum(text_lower.count(kw) for kw in keywords)
    if max(scores.values(), default=0) == 0:
        return "general"
    return max(scores, key=lambda k: scores[k])


def _detect_case_type(text: str) -> str:
    text_lower = text.lower()
    type_keywords = {
        "revenue_diversification": ["revenue diversification", "new revenue", "monetization", "revenue streams"],
        "cost_reduction": ["cost reduction", "cost cutting", "efficiency", "profitability", "margin"],
        "growth_strategy": ["growth strategy", "market expansion", "scale", "growth"],
        "organizational_change": ["restructuring", "reorganization", "change management", "transformation"],
        "turnaround": ["turnaround", "distressed", "struggling", "declining", "recovery"],
        "market_entry": ["market entry", "new market", "expansion", "launch"],
        "digital_transformation": ["digital transformation", "digitization", "technology adoption"],
    }
    scores = {}
    for case_type, keywords in type_keywords.items():
        scores[case_type] = sum(text_lower.count(kw) for kw in keywords)
    if max(scores.values(), default=0) == 0:
        return "general_strategy"
    return max(scores, key=lambda k: scores[k])
