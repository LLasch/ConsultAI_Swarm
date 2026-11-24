"""Parse PDFs and DOCX files into structured text."""

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def read_pdf(path: Path) -> dict:
    """Extract text and tables from a PDF file."""
    try:
        import pdfplumber
    except ImportError:
        return {"type": "pdf", "path": str(path), "text": "", "tables": [], "error": "pdfplumber not installed"}

    text_parts = []
    tables = []

    try:
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num}]\n{page_text}")

                # Extract tables
                page_tables = page.extract_tables()
                for tbl in page_tables:
                    if tbl:
                        md_table = _format_table_as_markdown(tbl)
                        tables.append({"page": page_num, "markdown": md_table})

        full_text = "\n\n".join(text_parts)
        if not full_text.strip():
            # Possibly scanned — flag it
            full_text = "[WARNING: No extractable text found — document may be scanned/image-based]"
            logger.warning(f"No text extracted from {path.name} — may be scanned")

        return {
            "type": "pdf",
            "path": str(path),
            "filename": path.name,
            "text": full_text,
            "tables": tables,
            "page_count": len(pdf.pages) if 'pdf' in dir() else 0,
        }
    except Exception as e:
        logger.error(f"Failed to parse PDF {path.name}: {e}")
        return {"type": "pdf", "path": str(path), "filename": path.name, "text": "", "tables": [], "error": str(e)}


def read_docx(path: Path) -> dict:
    """Extract text from a DOCX file preserving heading structure."""
    try:
        from docx import Document
    except ImportError:
        return {"type": "docx", "path": str(path), "text": "", "error": "python-docx not installed"}

    try:
        doc = Document(path)
        parts = []
        for para in doc.paragraphs:
            if para.style.name.startswith("Heading"):
                level = para.style.name.replace("Heading ", "").strip()
                try:
                    hashes = "#" * int(level)
                except ValueError:
                    hashes = "#"
                parts.append(f"{hashes} {para.text}")
            elif para.text.strip():
                parts.append(para.text)

        return {
            "type": "docx",
            "path": str(path),
            "filename": path.name,
            "text": "\n\n".join(parts),
        }
    except Exception as e:
        logger.error(f"Failed to parse DOCX {path.name}: {e}")
        return {"type": "docx", "path": str(path), "filename": path.name, "text": "", "error": str(e)}


def read_text(path: Path) -> dict:
    """Read plain text or markdown files."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "type": "text",
            "path": str(path),
            "filename": path.name,
            "text": text,
        }
    except Exception as e:
        logger.error(f"Failed to read text file {path.name}: {e}")
        return {"type": "text", "path": str(path), "filename": path.name, "text": "", "error": str(e)}


def _format_table_as_markdown(table: list) -> str:
    """Convert a list-of-lists table to markdown format."""
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(cell or "").replace("\n", " ") for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)
