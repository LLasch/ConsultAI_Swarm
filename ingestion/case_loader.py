"""Orchestrate all readers and build a unified case brief via Claude API."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console(file=sys.stdout)
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".txt": "text",
    ".md": "text",
    ".csv": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".xls": "spreadsheet",
}

# Skip these
IGNORE_FILES = {"case_brief.md", ".DS_Store", "Thumbs.db"}
IGNORE_EXTENSIONS = {".pptx", ".ppt"}  # existing slide decks aren't useful as text input


def load_case(case_dir: Path, console: Console = console) -> dict:
    """
    Read all materials from case_dir, extract content, generate a case brief.
    Returns dict with 'brief', 'files', 'brief_path'.
    """
    from ingestion.document_reader import read_pdf, read_docx, read_text
    from ingestion.spreadsheet_reader import read_spreadsheet
    from ingestion.interview_reader import parse_transcript

    files_content = []
    file_summaries = []

    console.print("\n[bold cyan][1/8] Ingesting case materials...[/bold cyan]")

    all_files = sorted([f for f in case_dir.rglob("*") if f.is_file() and f.name not in IGNORE_FILES])

    for file_path in all_files:
        ext = file_path.suffix.lower()
        if ext in IGNORE_EXTENSIONS:
            continue
        if ext not in SUPPORTED_EXTENSIONS:
            console.print(f"  [dim]↷ {file_path.name} — unsupported type, skipping[/dim]")
            continue

        file_type = SUPPORTED_EXTENSIONS[ext]
        result = None

        try:
            if ext == ".pdf":
                result = read_pdf(file_path)
                # Check if it looks like an interview transcript
                if _looks_like_interview(result.get("text", "")):
                    transcript_data = parse_transcript(result["text"], file_path.name)
                    result["interview_data"] = transcript_data
                    result["text"] = transcript_data["text"]
                    summary = f"  ✓ {file_path.name} — interview transcript, {len(transcript_data.get('speakers', []))} speakers"
                else:
                    tables_note = f", {len(result.get('tables', []))} tables" if result.get("tables") else ""
                    summary = f"  ✓ {file_path.name} — {result.get('page_count', '?')} pages{tables_note}"

            elif ext in (".docx", ".doc"):
                result = read_docx(file_path)
                if _looks_like_interview(result.get("text", "")):
                    transcript_data = parse_transcript(result["text"], file_path.name)
                    result["interview_data"] = transcript_data
                    result["text"] = transcript_data["text"]
                    summary = f"  ✓ {file_path.name} — interview transcript, {len(transcript_data.get('speakers', []))} speakers"
                else:
                    summary = f"  ✓ {file_path.name} — Word document"

            elif ext in (".csv", ".xlsx", ".xls"):
                result = read_spreadsheet(file_path)
                summary = f"  ✓ {file_path.name} — {result.get('sheet_count', 1)} sheet(s)"

            elif ext in (".txt", ".md"):
                result = read_text(file_path)
                if _looks_like_interview(result.get("text", "")):
                    transcript_data = parse_transcript(result["text"], file_path.name)
                    result["interview_data"] = transcript_data
                    result["text"] = transcript_data["text"]
                    summary = f"  ✓ {file_path.name} — interview transcript"
                else:
                    summary = f"  ✓ {file_path.name} — text/notes"

            if result:
                if result.get("error"):
                    console.print(f"  [yellow]⚠ {file_path.name} — parse error: {result['error']}[/yellow]")
                else:
                    console.print(summary)
                files_content.append(result)
                file_summaries.append({"filename": file_path.name, "summary": summary.strip()})

        except Exception as e:
            console.print(f"  [red]✗ {file_path.name} — failed: {e}[/red]")
            logger.error(f"Failed to process {file_path.name}: {e}", exc_info=True)

    if not files_content:
        raise ValueError(f"No readable files found in {case_dir}")

    # Generate case brief
    brief = _generate_case_brief(files_content, case_dir.name)
    brief_path = case_dir / "case_brief.md"
    brief_path.write_text(brief, encoding="utf-8")

    token_estimate = len(brief.split()) * 1.3
    console.print(f"  → Case brief generated ({int(token_estimate):,} tokens)")

    return {
        "brief": brief,
        "brief_path": brief_path,
        "files": files_content,
        "file_summaries": file_summaries,
        "case_name": case_dir.name,
    }


def _looks_like_interview(text: str) -> bool:
    """Heuristic: does this text look like an interview transcript?"""
    if not text:
        return False
    lines = text.split("\n")[:30]
    speaker_lines = sum(1 for l in lines if ":" in l and len(l) < 80 and l.split(":")[0].strip() and not l.startswith("http"))
    return speaker_lines >= 3


def _generate_case_brief(files_content: list, case_name: str) -> str:
    """Call Claude to synthesize all materials into a structured case brief."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()

    # Compile all content, truncating long sections
    combined_parts = [f"# Case Materials for: {case_name}\n"]
    total_chars = 0
    MAX_CHARS = 80000  # ~20k tokens input budget for the brief call

    for f in files_content:
        header = f"\n## File: {f.get('filename', 'unknown')}\n"
        text = f.get("text", "")
        # Truncate very long files
        if len(text) > 15000:
            text = text[:15000] + "\n\n[... truncated for brevity ...]"
        block = header + text
        if total_chars + len(block) > MAX_CHARS:
            break
        combined_parts.append(block)
        total_chars += len(block)

    all_content = "\n".join(combined_parts)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system = """You are a senior consulting analyst. Your job is to read raw case materials and produce a structured case brief that will be given to a panel of 50 consultant agents for analysis.

The brief must be under 6,000 tokens and must prioritize decision-relevant information. Be specific with numbers. Preserve key quotes from stakeholders. Note information gaps explicitly."""

    user = f"""Please analyze these case materials and produce a structured case brief with these exact sections:

1. **Client Overview** — Who is the client, what do they do, what is their mission/purpose
2. **Current Situation** — Financial position, operations, market context (include specific numbers)
3. **Key Challenges** — 3-6 clearly stated problems identified from the materials
4. **Stakeholder Perspectives** — Summarized views from interviews or stakeholder docs (include direct quotes)
5. **Financial Highlights** — Key metrics, trends, benchmarks, year-over-year changes
6. **Constraints** — Budget, timeline, political, regulatory, or organizational limitations
7. **Open Questions** — Information gaps or ambiguities the analyst panel should flag

Be concise, specific, and data-driven. Use bullet points liberally.

---

{all_content}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": user}],
        system=system,
    )

    brief_content = response.content[0].text
    return f"# Case Brief: {case_name}\n\n{brief_content}"
