"""Case management routes: list cases, learn, outcome, personas, knowledge status."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models import (
    CaseSummary,
    CasesResponse,
    KnowledgeStatusResponse,
    LearnRequest,
    OutcomeRequest,
    PersonaSummary,
)

router = APIRouter(tags=["cases"])


@router.get("/cases", response_model=CasesResponse, summary="List all active and archived cases")
def list_cases() -> CasesResponse:
    """
    Returns all cases in `cases/active/` and `cases/past/`, plus the number
    of cases indexed in the ChromaDB knowledge base.
    """
    active_cases: list[CaseSummary] = []
    archived_cases: list[CaseSummary] = []

    active_dir = Path("cases/active")
    if active_dir.exists():
        for case in sorted(active_dir.iterdir()):
            if not case.is_dir():
                continue
            has_brief = (case / "case_brief.md").exists()
            has_output = (Path("output") / case.name).exists()
            if has_output:
                status = "analyzed"
            elif has_brief:
                status = "brief_ready"
            else:
                status = "materials_only"
            active_cases.append(
                CaseSummary(name=case.name, status=status, has_brief=has_brief, has_output=has_output)
            )

    past_dir = Path("cases/past")
    if past_dir.exists():
        for case in sorted(past_dir.iterdir()):
            if not case.is_dir():
                continue
            meta_path = case / "metadata.json"
            if meta_path.exists():
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                archived_cases.append(
                    CaseSummary(
                        name=case.name,
                        status="archived",
                        has_brief=True,
                        has_output=True,
                        date_analyzed=meta.get("date_analyzed"),
                        top_recommendations=meta.get("top_recommendations", [])[:3],
                    )
                )
            else:
                archived_cases.append(CaseSummary(name=case.name, status="archived"))

    kb_count = 0
    try:
        from knowledge.vectorstore import list_cases as _list_kb
        kb_count = len(_list_kb())
    except Exception:
        pass

    return CasesResponse(active=active_cases, archived=archived_cases, knowledge_base_count=kb_count)


@router.post("/cases/learn", summary="Ingest a past case into the knowledge base")
def learn_case(request: LearnRequest) -> dict:
    """
    Chunk and embed a completed case directory into ChromaDB so it can be
    retrieved as context in future analyses.
    """
    from knowledge.ingest_past_case import ingest_case

    case_dir = Path(request.case_path)
    if not case_dir.exists() or not case_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Case directory not found: {request.case_path}")

    try:
        num_chunks = ingest_case(
            case_dir,
            override_industry=request.industry,
            override_case_type=request.case_type,
        )
        return {"case_name": case_dir.name, "chunks_ingested": num_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_name}/outcome", summary="Record outcome for an archived case")
def record_outcome(case_name: str, request: OutcomeRequest) -> dict:
    """
    Append an outcome note to `cases/past/{case_name}/outcome.md` and
    re-embed the updated case into the knowledge base.
    """
    from archive import add_outcome

    success = add_outcome(case_name, request.outcome_text)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{case_name}' not found or outcome could not be recorded.",
        )
    return {"case_name": case_name, "recorded": True}


@router.get(
    "/personas",
    response_model=list[PersonaSummary],
    summary="List all consultant personas",
)
def list_personas() -> list[PersonaSummary]:
    """Returns all 50+ consultant personas from `agents/personas.json`."""
    personas_path = Path(__file__).parent.parent.parent / "agents" / "personas.json"
    with open(personas_path, encoding="utf-8") as f:
        personas = json.load(f)
    return [PersonaSummary(**p) for p in personas]


@router.get(
    "/knowledge/status",
    response_model=KnowledgeStatusResponse,
    summary="Knowledge base status",
)
def knowledge_status() -> KnowledgeStatusResponse:
    """Returns the number of cases indexed in the ChromaDB knowledge base."""
    try:
        from knowledge.vectorstore import list_cases as _list_kb
        cases = _list_kb()
        return KnowledgeStatusResponse(cases_indexed=len(cases), case_names=sorted(cases))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
