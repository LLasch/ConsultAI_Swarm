"""
Slide deck generation — delegates to slide_builder.js (pptxgenjs / Node.js).
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import io, sys as _sys
if _sys.platform == "win32":
    _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(_sys.stdout, "buffer") else _sys.stdout
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console(file=_sys.stdout)

_JS_BUILDER = Path(__file__).parent / "slide_builder.js"


def build_slides(
    consensus: dict,
    case_name: str,
    round1_results: list,
    output_dir: Path = Path("output"),
    red_team: dict = None,
    pushback: dict = None,
    quant_analysis: dict = None,
    directions: list = None,
    case_tags: list = None,
) -> Path | None:
    """
    Build a PPTX slide deck by calling slide_builder.js via Node.js.
    Returns the output path, or None if it failed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = case_name.lower().replace(" ", "_").replace("/", "_")
    pptx_path = output_dir / f"{safe_name}_slides.pptx"

    # We need to pass round1 data for agent count — write a combined JSON
    combined_path = output_dir / "_slide_input.json"
    slide_input = {
        "consensus": consensus,
        "round1": round1_results,
        "red_team": red_team or {},
        "pushback": pushback or {},
        "quant_analysis": quant_analysis or {},
        "directions": directions or [],
        "case_tags": case_tags or [],
    }
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(slide_input, f, ensure_ascii=False)

    if not _JS_BUILDER.exists():
        console.print(f"  [yellow]slide_builder.js not found at {_JS_BUILDER} — skipping slides[/yellow]")
        return None

    # Check Node.js is available
    node_cmd = _find_node()
    if not node_cmd:
        console.print("  [yellow]Node.js not found — skipping slide generation. Install Node.js 18+ to enable.[/yellow]")
        return None

    try:
        result = subprocess.run(
            [node_cmd, str(_JS_BUILDER), str(combined_path), str(pptx_path), case_name],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0:
            console.print(f"  [green]Output:[/green] {pptx_path}")
            combined_path.unlink(missing_ok=True)
            return pptx_path
        else:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            # Check if it's a missing module error
            if "Cannot find module" in stderr and "pptxgenjs" in stderr:
                console.print("  [yellow]pptxgenjs not installed. Run: npm install  (in the project root)[/yellow]")
            else:
                console.print(f"  [yellow]slide_builder.js failed (exit {result.returncode})[/yellow]")
                if stderr:
                    console.print(f"  [dim]{stderr[:300]}[/dim]")
            combined_path.unlink(missing_ok=True)
            return None

    except subprocess.TimeoutExpired:
        console.print("  [yellow]Slide generation timed out[/yellow]")
        combined_path.unlink(missing_ok=True)
        return None
    except Exception as e:
        console.print(f"  [yellow]Slide generation error: {e}[/yellow]")
        combined_path.unlink(missing_ok=True)
        return None


def _find_node() -> str | None:
    """Find the node executable on the system PATH."""
    import shutil
    for candidate in ["node", "node.exe", "nodejs"]:
        path = shutil.which(candidate)
        if path:
            return path
    return None
