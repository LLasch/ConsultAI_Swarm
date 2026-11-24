# ADR-0001: FastAPI Sidecar as Python-Tauri Bridge

**Date**: 2026-03-22
**Status**: accepted
**Deciders**: Lucas

## Context

The desktop UI is built with Tauri (Rust core) + React. The consulting analysis pipeline is Python. Tauri's Rust core cannot directly invoke Python — a bridge is needed. The pipeline runs for 2-5 minutes, spawns 20 concurrent async agent calls, and must communicate real-time progress to the UI.

## Decision

We run a FastAPI server as a Tauri sidecar process on `localhost:8000`. Tauri manages its lifecycle (start on app open, kill on app close). The React frontend communicates with the Python pipeline exclusively via HTTP to `localhost:8000`.

## Alternatives Considered

### Alternative 1: Subprocess with stdout parsing
Tauri's Rust core spawns `python main.py analyze ...` and reads stdout line by line.

- **Pros**: Zero backend changes needed; existing CLI output reused
- **Cons**: No streaming — UI blocks until subprocess exits; stdout is Rich-formatted text not structured data; no way to push per-agent progress without major CLI refactoring; error handling is fragile
- **Why not**: A 20-agent run takes 2-5 minutes. A blocked UI is unacceptable for a chat-style interface.

### Alternative 2: Rewrite pipeline in Rust
Move the entire consulting engine into Tauri's Rust backend.

- **Pros**: Single binary, no Python dependency
- **Cons**: The pipeline depends on Anthropic's Python SDK, ChromaDB, sentence-transformers, pdfplumber, and python-docx — all Python-only libraries. Full rewrite would take weeks and lose parity with the CLI tool.
- **Why not**: Not feasible given dependency footprint and time constraints.

## Consequences

### Positive
- Structured JSON over HTTP — React can parse events without text scraping
- Real-time SSE streaming of per-agent and per-panel results (see ADR-0002)
- Pipeline logic stays in Python; no duplication
- FastAPI auto-generates OpenAPI docs at `/docs`
- The CLI (`main.py`) continues to work unchanged alongside the API

### Negative
- Python must be bundled with the Tauri app (or installed separately) for distribution
- Adds FastAPI + uvicorn as runtime dependencies
- Port conflict risk on `localhost:8000` (mitigated by making port configurable)

### Risks
- **Sidecar crash not surfaced to UI**: mitigated by health-check polling at `/health` on startup, with reconnect logic in the React client
