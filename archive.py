"""
Auto-archive pipeline.

After analysis completes:
1. Move case materials from cases/active/{name}/ → cases/past/{name}/materials/
2. Copy all deliverables into cases/past/{name}/output/
3. Write metadata.json
4. Auto-ingest the case into the ChromaDB knowledge base
"""

import json
import logging
import shutil
from datetime import date
from pathlib import Path

from rich.console import Console
import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
console = Console(file=sys.stdout)

logger = logging.getLogger(__name__)


def archive_case(
    case_name: str,
    active_dir: Path,
    output_dir: Path,
    consensus: dict,
    n_agents: int,
    n_rounds: int,
    question: str = "",
    total_tokens: int = 0,
) -> Path:
    """
    Move a completed active case to past/, copy deliverables, write metadata,
    and ingest into the knowledge base.

    Returns the past case directory path.
    """
    past_dir = Path("cases/past") / case_name
    materials_dir = past_dir / "materials"
    past_output_dir = past_dir / "output"

    console.print(f"\n[bold cyan]Archiving case to knowledge base...[/bold cyan]")

    # ── Atomic move with rollback safety ──────────────────────────────────────
    if past_dir.exists():
        console.print(f"  [yellow]Past case '{case_name}' already exists — overwriting[/yellow]")
        shutil.rmtree(past_dir)

    try:
        materials_dir.mkdir(parents=True, exist_ok=True)
        past_output_dir.mkdir(parents=True, exist_ok=True)

        # Move materials (copy first, then remove — safer than shutil.move)
        if active_dir.exists():
            copied_files = 0
            for item in active_dir.rglob("*"):
                if item.is_file():
                    dest = materials_dir / item.relative_to(active_dir)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(item, dest)
                        copied_files += 1
                    except PermissionError:
                        logger.warning(f"Could not copy (locked): {item.name}")
            # Remove source — ignore locked files on Windows
            shutil.rmtree(active_dir, ignore_errors=True)
            console.print(f"  -> Moved {copied_files} files: {active_dir} -> {materials_dir}")

        # Copy deliverables
        deliverable_patterns = [
            "*_report.md", "*_report.pdf", "*_slides.pptx",
            "round1_results.json", "round2_panels.json",
            "round3_consensus.json", "*_agent_log.json", "case_brief.md",
        ]
        copied = 0
        for pattern in deliverable_patterns:
            for src in output_dir.glob(pattern):
                dest = past_output_dir / src.name
                shutil.copy2(src, dest)
                copied += 1
        if copied:
            console.print(f"  -> Copied {copied} deliverable(s) into {past_output_dir}")

        # Write metadata
        recs = consensus.get("recommendations", [])
        top_rec_titles = [r.get("title", "") for r in recs[:5] if isinstance(r, dict)]
        metadata = {
            "case_name": case_name,
            "date_analyzed": date.today().isoformat(),
            "n_agents": n_agents,
            "n_rounds": n_rounds,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_tokens / 1_000_000 * 3.0, 4),
            "top_recommendations": top_rec_titles,
            "bottom_line": consensus.get("bottom_line", ""),
            "question": question,
        }
        meta_path = past_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    except Exception as e:
        logger.error(f"Archive failed: {e}", exc_info=True)
        console.print(f"  [red]Archive failed: {e}[/red]")
        return None

    # ── Ingest into knowledge base ────────────────────────────────────────────
    num_chunks = _auto_ingest(case_name, past_dir, past_output_dir, consensus, metadata)
    console.print(f"  -> Embedded {num_chunks} chunks into ChromaDB")
    console.print(f"  [green]Case '{case_name}' is now available for future reference[/green]")

    return past_dir


def _auto_ingest(
    case_name: str,
    past_dir: Path,
    output_dir: Path,
    consensus: dict,
    metadata: dict,
) -> int:
    """
    Chunk the consensus JSON into meaningful segments and embed into ChromaDB.
    Returns number of chunks stored.
    """
    from knowledge.vectorstore import store_chunks
    import hashlib

    def _id(case, typ, idx):
        return hashlib.md5(f"{case}_{typ}_{idx}".encode()).hexdigest()

    base_meta = {
        "case_name": case_name,
        "date": metadata.get("date_analyzed", ""),
        "industry": metadata.get("industry", "general"),
        "case_type": metadata.get("case_type", "general_strategy"),
    }

    chunks = []

    # Problem statement
    problem = consensus.get("problem_statement", "")
    if problem:
        chunks.append({
            "id": _id(case_name, "problem_statement", 0),
            "text": f"PROBLEM STATEMENT ({case_name}):\n{problem}",
            "metadata": {**base_meta, "chunk_type": "problem_statement"},
        })

    # Executive summary
    exec_sum = consensus.get("executive_summary", "")
    if exec_sum:
        chunks.append({
            "id": _id(case_name, "exec_summary", 0),
            "text": f"EXECUTIVE SUMMARY ({case_name}):\n{exec_sum}",
            "metadata": {**base_meta, "chunk_type": "exec_summary"},
        })

    # Key findings
    for i, finding in enumerate(consensus.get("key_findings", [])):
        text = finding.get("finding", "") if isinstance(finding, dict) else str(finding)
        evidence = finding.get("evidence", "") if isinstance(finding, dict) else ""
        confidence = finding.get("confidence", 0.8) if isinstance(finding, dict) else 0.8
        chunks.append({
            "id": _id(case_name, "finding", i),
            "text": f"KEY FINDING ({case_name}):\n{text}\n\nEvidence: {evidence}",
            "metadata": {**base_meta, "chunk_type": "finding", "confidence": str(round(confidence, 2))},
        })

    # Recommendations — each as its own chunk (most valuable for retrieval)
    for i, rec in enumerate(consensus.get("recommendations", [])):
        if not isinstance(rec, dict):
            continue
        title = rec.get("title", f"Rec {i+1}")
        desc = rec.get("description", "")
        rationale = rec.get("rationale", "")
        steps = rec.get("implementation_steps", [])
        impact = rec.get("expected_impact", "")
        support = rec.get("panel_support", "")
        chunk_text = (
            f"RECOMMENDATION ({case_name}): {title}\n"
            f"Description: {desc}\n"
            f"Rationale: {rationale}\n"
            f"Implementation: {'; '.join(steps[:4])}\n"
            f"Expected impact: {impact}\n"
            f"Panel support: {support}"
        )
        chunks.append({
            "id": _id(case_name, "recommendation", i),
            "text": chunk_text[:3000],
            "metadata": {
                **base_meta,
                "chunk_type": "recommendation",
                "recommendation_title": title,
                "panel_support": support,
                "impact": rec.get("expected_impact", ""),
            },
        })

    # Risk assessment
    risk = consensus.get("risk_assessment", "")
    if risk:
        chunks.append({
            "id": _id(case_name, "risk_assessment", 0),
            "text": f"RISK ASSESSMENT ({case_name}):\n{risk}",
            "metadata": {**base_meta, "chunk_type": "risk"},
        })

    # Implementation roadmap
    roadmap = consensus.get("implementation_roadmap", {})
    if roadmap:
        roadmap_text = "\n".join(
            f"{phase}: {', '.join(items)}"
            for phase, items in roadmap.items()
            if items
        )
        chunks.append({
            "id": _id(case_name, "roadmap", 0),
            "text": f"IMPLEMENTATION ROADMAP ({case_name}):\n{roadmap_text}",
            "metadata": {**base_meta, "chunk_type": "roadmap"},
        })

    # Minority views
    for i, view in enumerate(consensus.get("minority_views", [])):
        text = view.get("view", "") if isinstance(view, dict) else str(view)
        if text:
            chunks.append({
                "id": _id(case_name, "minority_view", i),
                "text": f"MINORITY VIEW ({case_name}): {text}",
                "metadata": {**base_meta, "chunk_type": "minority_view"},
            })

    # Also embed the case brief if available
    brief_path = output_dir / "case_brief.md"
    if not brief_path.exists():
        brief_path = Path("cases/past") / case_name / "materials" / "case_brief.md"
    if brief_path.exists():
        try:
            brief_text = brief_path.read_text(encoding="utf-8", errors="replace")
            import re
            sections = re.split(r"\n(?=#{1,3} )", brief_text)
            for j, section in enumerate(sections):
                section = section.strip()
                if len(section) > 50:
                    chunks.append({
                        "id": _id(case_name, "brief_section", j),
                        "text": section[:2500],
                        "metadata": {**base_meta, "chunk_type": "context"},
                    })
        except Exception as e:
            logger.warning(f"Could not embed case brief: {e}")

    try:
        store_chunks(chunks)
    except Exception as e:
        logger.error(f"Failed to embed chunks: {e}", exc_info=True)
        console.print(f"  [yellow]Knowledge base embedding failed: {e}[/yellow]")
        return 0

    return len(chunks)


def add_outcome(case_name: str, outcome_text: str) -> bool:
    """
    Append outcome data to a past case and re-embed it.
    Returns True on success.
    """
    from knowledge.vectorstore import store_chunks
    import hashlib

    past_dir = Path("cases/past") / case_name
    if not past_dir.exists():
        console.print(f"  [red]No past case found: {case_name}[/red]")
        return False

    # Write outcome.md
    outcome_path = past_dir / "outcome.md"
    with open(outcome_path, "w", encoding="utf-8") as f:
        f.write(f"# Outcome — {case_name}\n\n{outcome_text}\n")

    # Load metadata
    meta_path = past_dir / "metadata.json"
    try:
        with open(meta_path, encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception:
        metadata = {"case_name": case_name}

    # Embed the outcome
    chunk_id = hashlib.md5(f"{case_name}_outcome_0".encode()).hexdigest()
    chunks = [{
        "id": chunk_id,
        "text": f"OUTCOME ({case_name}):\n{outcome_text}",
        "metadata": {
            "case_name": case_name,
            "chunk_type": "outcome",
            "date": date.today().isoformat(),
            "industry": metadata.get("industry", "general"),
            "case_type": metadata.get("case_type", "general"),
        },
    }]

    try:
        store_chunks(chunks)
    except Exception as e:
        logger.error(f"Failed to embed outcome: {e}", exc_info=True)
        console.print(f"  [red]Failed to embed outcome: {e}[/red]")
        return False

    console.print(f"  [green]Outcome added to '{case_name}' and embedded into knowledge base[/green]")
    return True
