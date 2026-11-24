"""Pydantic models for API request/response types and SSE event payloads."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    case_path: str = Field(..., description="Absolute or relative path to the case materials directory")
    question: Optional[str] = Field(None, description="Specific strategic question to focus on")
    agents: int = Field(20, ge=1, le=20, description="Number of consultant agents (max 20)")
    rounds: int = Field(3, ge=1, le=3, description="Number of deliberation rounds (1–3)")
    output_dir: str = Field("output", description="Directory to write deliverables into")
    no_archive: bool = Field(False, description="Skip auto-archiving after analysis completes")


class LearnRequest(BaseModel):
    case_path: str = Field(..., description="Path to a past case directory to ingest into the knowledge base")
    industry: Optional[str] = Field(None, description="Industry tag, e.g. nonprofit, healthcare, retail")
    case_type: Optional[str] = Field(None, description="Case type, e.g. revenue_diversification, turnaround")


class OutcomeRequest(BaseModel):
    outcome_text: str = Field(..., description="Outcome description to record and re-embed into the knowledge base")


# ── Response models ───────────────────────────────────────────────────────────

class CaseSummary(BaseModel):
    name: str
    status: str  # "materials_only" | "brief_ready" | "analyzed" | "archived"
    has_brief: bool = False
    has_output: bool = False
    date_analyzed: Optional[str] = None
    top_recommendations: list[str] = []


class CasesResponse(BaseModel):
    active: list[CaseSummary]
    archived: list[CaseSummary]
    knowledge_base_count: int


class PersonaSummary(BaseModel):
    id: str
    name: str
    persona: str
    expertise: list[str]
    thinking_style: str
    seniority: str


class KnowledgeStatusResponse(BaseModel):
    cases_indexed: int
    case_names: list[str]


# ── SSE event data shapes (informational — not validated at runtime) ──────────
#
# Each SSE event has the form:
#   event: <event_type>
#   data: <JSON payload>
#
# Event types and their data payloads:
#
#   started            {"case_name", "agents", "rounds", "estimated_cost"}
#   case_brief_started {"case_name"}
#   case_brief_complete{"brief_preview"}           # first 300 chars of brief
#   retrieval_complete {"similar_cases"}            # list[str] of case names found
#   round1_started     {"agent_count"}
#   agent_complete     {"id", "name", "expertise", "seniority", "thinking_style",
#                       "key_insight", "key_problems", "recommendations",
#                       "dissenting_view"}
#   round1_complete    {"agents_succeeded", "agents_total"}
#   round2_started     {"panel_count"}
#   panel_complete     {"panel_num", "agents", "result"}
#   round2_complete    {"panels_succeeded"}
#   round3_started     {}
#   consensus_complete {"consensus"}                # full consensus dict
#   report_complete    {"output_dir"}
#   done               {}
#   error              {"message"}
