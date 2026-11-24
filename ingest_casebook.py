#!/usr/bin/env python3
"""
ingest_casebook.py — Extract individual cases from a PDF casebook and load them
into the Simsultant knowledge base.

Steps per PDF:
  1. Extract text with pdfplumber (one pass, no API cost)
  2. One Sonnet call to identify case boundaries (page ranges)
  3. One Haiku call per case to extract structured metadata
  4. Write case_brief.md + metadata.json under cases/past/{slug}/
  5. Embed directly into ChromaDB (skips redundant brief-generation call)

Usage:
    python ingest_casebook.py rawcasebooks/Columbia_2006.pdf
    python ingest_casebook.py rawcasebooks/Columbia_2006.pdf rawcasebooks/Wharton_2019.pdf
"""

import argparse
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeElapsedColumn

load_dotenv()
console = Console(file=sys.stdout)
logging.basicConfig(level=logging.WARNING)


# ──────────────────────────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────────────────────────

BOUNDARY_SYSTEM = """You are an expert at analyzing business school casebooks. Your job is to identify the boundaries of individual cases within a PDF."""

BOUNDARY_USER = """This PDF casebook has {total_pages} pages. Below is the extracted text with page markers like [PAGE 1], [PAGE 2], etc.

Identify every distinct case in this document. A case typically has a title, company name, background section, and discussion questions. Table of contents, prefaces, and appendices are NOT cases.

Return ONLY a JSON array — no other text, no markdown fences:
[
  {{
    "case_num": 1,
    "title": "Full case title",
    "company": "Company name",
    "start_page": 1,
    "end_page": 14
  }},
  ...
]

If you cannot determine boundaries precisely, estimate from the text structure.

PDF text (first {sample_pages} pages shown):
{text_sample}"""

EXTRACTION_USER = """Extract structured information from this business school case.

Return ONLY this JSON object — no other text, no markdown fences:
{{
  "title": "exact case title",
  "company": "company or organization name",
  "industry": "one-word industry (e.g. retail, healthcare, nonprofit, saas, manufacturing, finance, education, technology)",
  "case_type": "one of: growth_strategy, revenue_diversification, cost_reduction, turnaround, market_entry, organizational_change, digital_transformation, pricing_strategy, general_strategy",
  "problem": "2-3 sentence description of the core business problem or decision",
  "context": "3-5 sentences of relevant background: company history, market position, financials",
  "decision": "what decision or action did the company take? (or 'Not specified' if a teaching case)",
  "outcome": "what was the result? Include numbers if available. (or 'Not disclosed' if not provided)",
  "questions": ["discussion question 1", "discussion question 2"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Tags should be specific and useful for retrieval (e.g. 'pricing', 'market_entry', 'nonprofit', 'membership', 'turnaround', 'china', 'b2b').

Case text:
{case_text}"""


# ──────────────────────────────────────────────────────────────────────────────
# PDF extraction
# ──────────────────────────────────────────────────────────────────────────────

def extract_pages(pdf_path: Path) -> list[str]:
    """
    Extract text from each page. Returns list of page texts (index 0 = page 1).
    """
    try:
        import pdfplumber
    except ImportError:
        console.print("[red]pdfplumber not installed. Run: pip install pdfplumber[/red]")
        sys.exit(1)

    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            try:
                text = page.extract_text() or ""
                # Also extract tables as simple text
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if row:
                            text += "\n" + " | ".join(str(c or "") for c in row)
            except Exception:
                text = ""
            pages.append(text)

    return pages


def build_text_sample(pages: list[str], max_chars: int = 60000) -> str:
    """
    Build page-marked text sample for boundary detection.
    Include as many pages as fit within max_chars.
    """
    parts = []
    total = 0
    for i, text in enumerate(pages):
        marker = f"\n[PAGE {i + 1}]\n"
        chunk = marker + text.strip()
        if total + len(chunk) > max_chars:
            parts.append(f"\n[... {len(pages) - i} more pages not shown ...]")
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────────────────────────────────────

def _call_api(model: str, system: str, user: str, max_tokens: int = 2000) -> str:
    """Single synchronous API call. Returns raw text content."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        payload["system"] = system

    for attempt in range(4):
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 2 ** attempt * 5
                console.print(f"  [yellow]Rate limited, waiting {wait}s...[/yellow]")
                time.sleep(wait)
            else:
                raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("API call failed after retries")


def _parse_json(text: str) -> object:
    """Parse JSON from model response, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[\{][\s\S]+[\]\}]", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Could not parse JSON from response: {text[:300]}")


# ──────────────────────────────────────────────────────────────────────────────
# Boundary detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_boundaries(pages: list[str], pdf_name: str) -> list[dict]:
    """
    One Sonnet call to identify case boundaries in the PDF.
    Returns list of {"case_num", "title", "company", "start_page", "end_page"}.
    """
    total_pages = len(pages)
    # Show up to 80 pages for boundary detection; most casebooks fit in that window
    sample_pages = min(total_pages, 80)
    text_sample = build_text_sample(pages[:sample_pages], max_chars=55000)

    console.print(f"  -> Sending {sample_pages}/{total_pages} pages to boundary detector...")

    user = BOUNDARY_USER.format(
        total_pages=total_pages,
        sample_pages=sample_pages,
        text_sample=text_sample,
    )

    raw = _call_api("claude-sonnet-4-20250514", BOUNDARY_SYSTEM, user, max_tokens=2000)
    boundaries = _parse_json(raw)

    if not isinstance(boundaries, list):
        raise ValueError(f"Expected list of boundaries, got: {type(boundaries)}")

    # Clamp page numbers to valid range
    for b in boundaries:
        b["start_page"] = max(1, int(b.get("start_page", 1)))
        b["end_page"] = min(total_pages, int(b.get("end_page", total_pages)))

    return boundaries


# ──────────────────────────────────────────────────────────────────────────────
# Per-case extraction
# ──────────────────────────────────────────────────────────────────────────────

def extract_case_text(pages: list[str], start_page: int, end_page: int) -> str:
    """Concatenate pages for a given range (1-indexed). Truncates to ~8000 chars."""
    parts = []
    for i in range(start_page - 1, min(end_page, len(pages))):
        parts.append(f"[PAGE {i + 1}]\n{pages[i]}")
    text = "\n\n".join(parts)
    return text[:8000] if len(text) > 8000 else text


def extract_case_metadata(case_text: str, boundary: dict) -> dict:
    """One Haiku call to extract structured case metadata."""
    user = EXTRACTION_USER.format(case_text=case_text)
    raw = _call_api("claude-haiku-4-5-20251001", "", user, max_tokens=1200)

    try:
        data = _parse_json(raw)
    except ValueError:
        # Fallback with data from boundary detection
        data = {}

    # Fill in from boundary detection if Haiku left fields empty
    if not data.get("title"):
        data["title"] = boundary.get("title", f"Case {boundary['case_num']}")
    if not data.get("company"):
        data["company"] = boundary.get("company", "Unknown")
    if not data.get("industry"):
        data["industry"] = "general"
    if not data.get("case_type"):
        data["case_type"] = "general_strategy"
    if not data.get("tags"):
        data["tags"] = [data.get("industry", "strategy")]

    return data


# ──────────────────────────────────────────────────────────────────────────────
# Case saving
# ──────────────────────────────────────────────────────────────────────────────

def slugify(title: str) -> str:
    """Convert a case title to a safe directory name."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:60] or "case"


def build_brief_md(data: dict, source_pdf: str, page_range: str) -> str:
    """Format extracted case metadata as a structured case_brief.md."""
    tags_str = ", ".join(data.get("tags", []))
    questions = data.get("questions", [])
    questions_md = "\n".join(f"- {q}" for q in questions) if questions else "_Not provided_"

    return f"""# Case Brief: {data.get('title', 'Untitled')}

**Company:** {data.get('company', 'Unknown')}
**Industry:** {data.get('industry', 'General')}
**Source:** {source_pdf} (pages {page_range})
**Tags:** {tags_str}

---

## Current Situation

{data.get('context', '_Not extracted_')}

## Key Challenges

{data.get('problem', '_Not extracted_')}

## Decision

{data.get('decision', '_Not specified_')}

## Outcome

{data.get('outcome', '_Not disclosed_')}

## Discussion Questions

{questions_md}
"""


def save_case(data: dict, source_pdf: str, page_range: str, base_dir: Path) -> Path:
    """
    Write case files under cases/past/{slug}/.
    Returns the case directory path.
    """
    slug = slugify(data.get("title", "case"))

    # Avoid collisions — append number if slug already exists
    case_dir = base_dir / slug
    counter = 1
    while case_dir.exists():
        case_dir = base_dir / f"{slug}-{counter}"
        counter += 1

    materials_dir = case_dir / "materials"
    materials_dir.mkdir(parents=True)

    # case_brief.md (what the knowledge base embeds)
    brief_md = build_brief_md(data, source_pdf, page_range)
    (materials_dir / "case_brief.md").write_text(brief_md, encoding="utf-8")

    # metadata.json
    metadata = {
        "case_name": case_dir.name,
        "title": data.get("title", ""),
        "company": data.get("company", ""),
        "industry": data.get("industry", "general"),
        "case_type": data.get("case_type", "general_strategy"),
        "source_pdf": source_pdf,
        "page_range": page_range,
        "tags": data.get("tags", []),
        "date_ingested": date.today().isoformat(),
        "n_agents": 0,
        "n_rounds": 0,
        "total_tokens": 0,
        "total_cost_usd": 0,
        "top_recommendations": [],
        "bottom_line": data.get("outcome", ""),
        "question": "",
    }
    (case_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return case_dir


# ──────────────────────────────────────────────────────────────────────────────
# ChromaDB ingestion
# ──────────────────────────────────────────────────────────────────────────────

def embed_case(data: dict, case_name: str) -> int:
    """
    Embed case directly into ChromaDB. Skips the load_case Sonnet call.
    Returns number of chunks stored.
    """
    from knowledge.vectorstore import store_chunks

    def _id(name: str, kind: str, idx: int = 0) -> str:
        return hashlib.md5(f"{name}_{kind}_{idx}".encode()).hexdigest()

    base_meta = {
        "case_name": case_name,
        "industry": data.get("industry", "general"),
        "case_type": data.get("case_type", "general_strategy"),
        "date": date.today().isoformat(),
        "source": "casebook",
    }

    chunks = []

    # Problem statement
    problem = data.get("problem", "")
    if problem:
        chunks.append({
            "id": _id(case_name, "problem"),
            "text": f"PROBLEM STATEMENT ({case_name} — {data.get('company', '')}):\n{problem}",
            "metadata": {**base_meta, "chunk_type": "problem_statement"},
        })

    # Context / background
    context = data.get("context", "")
    if context:
        chunks.append({
            "id": _id(case_name, "context"),
            "text": f"CONTEXT ({case_name} — {data.get('company', '')}):\n{context}",
            "metadata": {**base_meta, "chunk_type": "exec_summary"},
        })

    # Decision
    decision = data.get("decision", "")
    if decision and decision.lower() not in ("not specified", ""):
        chunks.append({
            "id": _id(case_name, "decision"),
            "text": f"DECISION ({case_name}):\n{decision}",
            "metadata": {**base_meta, "chunk_type": "recommendation"},
        })

    # Outcome
    outcome = data.get("outcome", "")
    if outcome and outcome.lower() not in ("not disclosed", ""):
        chunks.append({
            "id": _id(case_name, "outcome"),
            "text": f"OUTCOME ({case_name}):\n{outcome}",
            "metadata": {**base_meta, "chunk_type": "outcome"},
        })

    # Full brief as one additional chunk
    title = data.get("title", case_name)
    company = data.get("company", "")
    tags = ", ".join(data.get("tags", []))
    full_text = (
        f"CASE STUDY ({case_name}): {title} | {company}\n"
        f"Industry: {data.get('industry')} | Tags: {tags}\n"
        f"Problem: {problem}\n"
        f"Context: {context}\n"
        f"Decision: {decision}\n"
        f"Outcome: {outcome}"
    )
    chunks.append({
        "id": _id(case_name, "full_brief"),
        "text": full_text[:3000],
        "metadata": {**base_meta, "chunk_type": "context"},
    })

    store_chunks(chunks)
    return len(chunks)


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path, past_dir: Path) -> list[dict]:
    """
    Process one PDF casebook. Returns list of result dicts.
    """
    console.print(Rule(f"[bold blue]{pdf_path.name}[/bold blue]"))

    # 1. Extract all pages
    console.print("\n[bold cyan][1/3] Extracting PDF text...[/bold cyan]")
    pages = extract_pages(pdf_path)
    console.print(f"  -> {len(pages)} pages extracted")

    if not pages or all(not p.strip() for p in pages):
        console.print("[red]  No text extracted — PDF may be scanned/image-only. Skipping.[/red]")
        return []

    # 2. Detect case boundaries
    console.print("\n[bold cyan][2/3] Detecting case boundaries (Sonnet)...[/bold cyan]")
    try:
        boundaries = detect_boundaries(pages, pdf_path.name)
        console.print(f"  -> Found {len(boundaries)} case(s)")
        for b in boundaries:
            console.print(f"     Case {b['case_num']}: \"{b.get('title', '?')}\" (pp. {b['start_page']}–{b['end_page']})")
    except Exception as e:
        console.print(f"[red]  Boundary detection failed: {e}[/red]")
        return []

    if not boundaries:
        console.print("[yellow]  No cases detected in this PDF.[/yellow]")
        return []

    # 3. Extract and save each case
    console.print(f"\n[bold cyan][3/3] Extracting and ingesting {len(boundaries)} case(s) (Haiku)...[/bold cyan]")
    results = []

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(), TaskProgressColumn(), TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  Processing", total=len(boundaries))

        for boundary in boundaries:
            case_num = boundary.get("case_num", "?")
            title_hint = boundary.get("title", f"Case {case_num}")

            try:
                # Extract case text
                case_text = extract_case_text(pages, boundary["start_page"], boundary["end_page"])

                # Haiku extraction
                data = extract_case_metadata(case_text, boundary)

                # Save files
                page_range = f"{boundary['start_page']}–{boundary['end_page']}"
                case_dir = save_case(data, pdf_path.name, page_range, past_dir)

                # Embed into ChromaDB
                n_chunks = embed_case(data, case_dir.name)

                results.append({
                    "case_name": case_dir.name,
                    "title": data.get("title", title_hint),
                    "company": data.get("company", ""),
                    "industry": data.get("industry", ""),
                    "chunks": n_chunks,
                    "dir": str(case_dir),
                    "success": True,
                })

            except Exception as e:
                console.print(f"\n  [red]✗ Case {case_num} (\"{title_hint}\"): {e}[/red]")
                results.append({
                    "case_name": title_hint,
                    "success": False,
                    "error": str(e),
                })

            progress.advance(task)
            # Small pause to respect rate limits between Haiku calls
            time.sleep(0.5)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ingest PDF casebooks into the Simsultant knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="PDF casebook file(s) to ingest")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("cases/past"),
        help="Directory to save extracted cases (default: cases/past/)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Detect boundaries and show case list without extracting or saving",
    )
    args = parser.parse_args()

    # Validate API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Add it to .env[/red]")
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_cost_estimate = 0.0

    for pdf_path in args.pdfs:
        if not pdf_path.exists():
            console.print(f"[red]File not found: {pdf_path}[/red]")
            continue
        if pdf_path.suffix.lower() != ".pdf":
            console.print(f"[yellow]Skipping non-PDF: {pdf_path}[/yellow]")
            continue

        if args.dry_run:
            console.print(Rule(f"[bold blue]{pdf_path.name} (dry run)[/bold blue]"))
            pages = extract_pages(pdf_path)
            console.print(f"  {len(pages)} pages")
            try:
                boundaries = detect_boundaries(pages, pdf_path.name)
                console.print(f"  {len(boundaries)} cases detected:")
                for b in boundaries:
                    console.print(f"    {b['case_num']}. {b.get('title', '?')} (pp. {b['start_page']}–{b['end_page']})")
                n_cases = len(boundaries)
                est = 8000 / 1e6 * 3.0 + n_cases * 1200 / 1e6 * 0.25
                console.print(f"  Estimated cost if fully ingested: ~${est:.3f}")
            except Exception as e:
                console.print(f"  [red]Boundary detection failed: {e}[/red]")
            continue

        results = process_pdf(pdf_path, args.output_dir)
        all_results.extend(results)

        # Rough cost: 1 Sonnet call + N Haiku calls
        n_cases = len(results)
        cost = 8000 / 1e6 * 3.0 + n_cases * 1200 / 1e6 * 0.25
        total_cost_estimate += cost

    if args.dry_run:
        return

    # Summary
    console.print(Rule("[bold green]Ingestion Complete[/bold green]"))
    succeeded = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]

    console.print(f"\n[green]✓ {len(succeeded)} case(s) successfully ingested[/green]")
    for r in succeeded:
        console.print(f"  • {r['title']} ({r.get('company', '')}) → {r['case_name']} [{r['chunks']} chunks]")

    if failed:
        console.print(f"\n[red]✗ {len(failed)} case(s) failed[/red]")
        for r in failed:
            console.print(f"  • {r['case_name']}: {r.get('error', 'unknown error')}")

    console.print(f"\n[dim]Estimated API cost: ~${total_cost_estimate:.3f}[/dim]")
    console.print(f"[dim]Cases saved to: {args.output_dir.resolve()}[/dim]")

    # Verify KB
    try:
        from knowledge.vectorstore import list_cases
        kb_cases = list_cases()
        console.print(f"[dim]Knowledge base now contains {len(kb_cases)} case(s)[/dim]")
    except Exception:
        pass


if __name__ == "__main__":
    main()
