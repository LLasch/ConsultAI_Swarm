"""SSE streaming endpoint — POST /analyze."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.models import AnalyzeRequest
from api import pipeline_runner

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post(
    "",
    summary="Run full consulting analysis (SSE stream)",
    response_description="text/event-stream of named SSE events",
)
async def analyze(request: AnalyzeRequest) -> StreamingResponse:
    """
    Start a consulting analysis and stream progress as Server-Sent Events.

    **Response format** — `Content-Type: text/event-stream`.
    Each message:
    ```
    event: <event_type>
    data: <JSON payload>

    ```

    **Event sequence** (in order):

    | Event | Payload fields | Notes |
    |---|---|---|
    | `started` | `case_name`, `agents`, `rounds`, `estimated_cost` | First event |
    | `case_brief_started` | `case_name` | Ingestion underway |
    | `case_brief_complete` | `brief_preview` | First 300 chars of generated brief |
    | `retrieval_complete` | `similar_cases` | List of matched past case names |
    | `round1_started` | `agent_count` | |
    | `agent_complete` | `id`, `name`, `expertise`, `seniority`, `thinking_style`, `key_insight`, `key_problems`, `recommendations`, `dissenting_view` | Fires once per agent |
    | `round1_complete` | `agents_succeeded`, `agents_total` | |
    | `round2_started` | `panel_count` | Only if `rounds >= 2` |
    | `panel_complete` | `panel_num`, `agents`, `result` | Fires once per panel |
    | `round2_complete` | `panels_succeeded` | |
    | `round3_started` | *(empty)* | Only if `rounds >= 3` |
    | `consensus_complete` | `consensus` | Full consensus JSON |
    | `report_complete` | `output_dir` | Deliverables written to disk |
    | `done` | *(empty)* | Terminal success |
    | `error` | `message` | Terminal failure |

    **Client usage (fetch + ReadableStream — recommended for Tauri):**
    ```js
    const resp = await fetch("http://localhost:8000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\\n\\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const eventLine = part.match(/^event: (.+)$/m)?.[1];
        const dataLine = part.match(/^data: (.+)$/m)?.[1];
        if (eventLine && dataLine) {
          onEvent(eventLine, JSON.parse(dataLine));
        }
      }
    }
    ```

    Note: Use `fetch` (not `EventSource`) because `EventSource` does not support POST bodies.
    """
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.create_task(pipeline_runner.run_analysis(request, queue))

    async def event_stream():
        while True:
            event = await queue.get()
            event_type = event["type"]
            data = json.dumps(event.get("data", {}), default=str)
            yield f"event: {event_type}\ndata: {data}\n\n"
            if event_type in ("done", "error"):
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind a proxy
        },
    )
