from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from alphagraph.schemas import ApproveRunRequest, CreateRunRequest


router = APIRouter()


@router.post("/runs", status_code=201)
def create_run(request: Request, payload: CreateRunRequest):
    service = request.app.state.service
    snapshot = service.create_run(payload.brief)
    return snapshot.model_dump()


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request):
    service = request.app.state.service
    try:
        snapshot = service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return snapshot.model_dump()


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str, payload: ApproveRunRequest, request: Request):
    service = request.app.state.service
    try:
        snapshot = service.approve_run(run_id, approved=payload.approved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return snapshot.model_dump()


@router.get("/runs/{run_id}/artifacts/{name}")
def fetch_artifact(run_id: str, name: str, request: Request):
    service = request.app.state.service
    try:
        snapshot = service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc

    candidate_paths = [snapshot.final_report_path, *snapshot.artifact_paths.values()]
    for attempt in snapshot.attempts:
        candidate_paths.extend(attempt.artifact_paths.values())
    for raw_path in candidate_paths:
        if raw_path is None:
            continue
        path = Path(raw_path)
        if path.name == name and path.exists():
            return PlainTextResponse(path.read_text())
    raise HTTPException(status_code=404, detail="Artifact not found")
