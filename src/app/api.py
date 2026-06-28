from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.app import repository
from src.config import settings

app = FastAPI(title="AdShield AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class FeedbackInput(BaseModel):
    case_id: str
    decision: str
    notes: str = ""


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "database_ready": settings.db_path.exists(), "real_data_only": True}


@app.get("/api/overview")
def get_overview() -> dict[str, object]:
    return repository.overview()


@app.get("/api/cases")
def get_cases(search: str = "", category: str = "", severity: str = "", language: str = "", source: str = "", action: str = "", limit: int = Query(200, ge=1, le=1000)) -> list[dict[str, object]]:
    return repository.cases(search, category, severity, language, source, action, limit)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, object]:
    result = repository.case_detail(case_id)
    if not result:
        raise HTTPException(404, "Case not found")
    return result


@app.get("/api/metrics")
def get_metrics() -> dict[str, object]:
    return repository.metrics()


@app.get("/api/policies")
def get_policies() -> list[dict[str, object]]:
    return repository.policies()


@app.get("/api/mandarin")
def get_mandarin() -> dict[str, object]:
    return repository.mandarin_lab()


@app.post("/api/feedback")
def post_feedback(payload: FeedbackInput) -> dict[str, object]:
    try:
        return repository.save_feedback(payload.case_id, payload.decision, payload.notes)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


dist = settings.root / "dist"
if dist.exists():
    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        candidate = dist / path
        return FileResponse(candidate if candidate.is_file() else dist / "index.html")


if __name__ == "__main__":
    uvicorn.run("src.app.api:app", host="127.0.0.1", port=8501, reload=False)
