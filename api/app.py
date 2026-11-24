"""
Simsultant FastAPI server.

Start with:
    uvicorn api.app:app --reload --port 8000

Or from the project root:
    python -m uvicorn api.app:app --port 8000
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is on sys.path so sibling packages (agents, ingestion,
# knowledge, deliverables, archive) are importable from within the api/ package.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from api.routes.analyze import router as analyze_router
from api.routes.cases import router as cases_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "[WARNING] ANTHROPIC_API_KEY is not set. "
            "Analysis calls will fail. Add it to .env or set the environment variable.",
            file=sys.stderr,
        )
    yield
    # Nothing to clean up on shutdown.


app = FastAPI(
    title="Simsultant API",
    description=(
        "Multi-agent AI consulting analysis engine. "
        "Run full 3-round deliberation pipelines and stream results in real time."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Tauri webview origins and local dev servers.
# Tauri wraps the webview in a custom protocol — origins vary by platform.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",          # Tauri v1 macOS/Linux
        "https://tauri.localhost",    # Tauri v2
        "http://localhost:1420",      # Tauri v2 dev server default
        "http://localhost:5173",      # Vite dev server default
        "http://localhost:3000",      # CRA / other dev servers
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(cases_router)


@app.get("/health", tags=["meta"], summary="Health check")
def health() -> dict:
    """Returns server status and whether the Anthropic API key is configured."""
    return {
        "status": "ok",
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
