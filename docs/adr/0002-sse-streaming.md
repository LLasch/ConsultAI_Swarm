# ADR-0002: Server-Sent Events for Pipeline Streaming

**Date**: 2026-03-22
**Status**: accepted
**Deciders**: Lucas

## Context

The 3-round consulting pipeline takes 2-5 minutes and produces results progressively: 20 agents complete one at a time in Round 1, then 4 panels in Round 2, then a single consensus in Round 3. The UI needs to display each agent's key insight as it arrives, not wait for the full pipeline to finish. A request-response model is insufficient.

## Decision

We use Server-Sent Events (SSE) on `POST /analyze`. The endpoint returns `Content-Type: text/event-stream` and emits named events (`agent_complete`, `panel_complete`, `consensus_complete`, etc.) with JSON payloads as each pipeline stage completes. The asyncio pipeline uses a `queue: asyncio.Queue` to decouple event production from HTTP delivery.

## Alternatives Considered

### Alternative 1: WebSocket
Full duplex connection — client and server can both send messages.

- **Pros**: Bidirectional (could support "stop analysis" command); standard for real-time apps
- **Cons**: More complex setup (handshake, ping/pong, reconnection); FastAPI WebSocket support requires explicit lifecycle management; overkill since data only flows server→client during a pipeline run
- **Why not**: The pipeline is unidirectional — the server pushes events, the client only reads. WebSocket's bidirectional complexity buys nothing here.

### Alternative 2: HTTP polling
Client polls `GET /analyze/{job_id}/status` every N seconds.

- **Pros**: Stateless, dead simple, works through any proxy
- **Cons**: Latency proportional to poll interval; wastes requests; agent results arrive faster than any polling interval that avoids rate-limiting the server
- **Why not**: We want agent results to appear in the UI within 1-2 seconds of completion. Polling at that frequency is wasteful and creates unnecessary load.

### Alternative 3: Long-polling
Client holds open a request; server responds when an event is ready, client immediately re-requests.

- **Pros**: Works without SSE support
- **Cons**: More complex client code; one event per round-trip; connection management overhead
- **Why not**: SSE is a first-class browser/Tauri feature. Long-polling is a workaround from before SSE was universally supported.

## Consequences

### Positive
- Agents appear in the UI one at a time as they complete — no waiting for the full pipeline
- SSE is natively supported by the browser `EventSource` API and Tauri webviews
- Server implementation is simple: `StreamingResponse` + `asyncio.Queue` in FastAPI
- Natural backpressure: if the client reads slowly, the queue fills, and the producer awaits

### Negative
- SSE is unidirectional — a "cancel analysis" feature requires a separate `POST /analyze/cancel` endpoint (future work)
- The `POST /analyze` SSE pattern is non-standard (SSE is typically on GET); documented in OpenAPI but may surprise API consumers
- Connection drops mid-stream mean the full pipeline must re-run (no resume); mitigated by saving partial results to disk at each round

### Risks
- **Tauri webview SSE support**: Tauri uses a system webview (WebKit/Edge) which supports `EventSource` and `fetch` streaming. The React client should use `fetch` with `ReadableStream` rather than `EventSource` since `EventSource` doesn't support POST bodies.
