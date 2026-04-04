"""App FastAPI principal que sirve API y frontend React."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.core.services import BASE_DIR, get_service


FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(title="Balance de Masas Cu/H2SO4 API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta() -> dict:
    service = get_service()
    return {
        "app": "Balance de Masas Cu/H2SO4",
        "stack": "FastAPI + React",
        "heap": service.get_heap_meta(),
    }


@app.get("/api/monthly/overview")
def get_monthly_overview() -> dict:
    return get_service().get_dashboard_bundle()


@app.get("/api/monthly/raw")
def get_monthly_raw() -> list:
    return get_service().get_dashboard_bundle()["tables"]["raw"]


@app.get("/api/inventory/piles")
def get_inventory() -> list:
    return get_service().get_dashboard_bundle()["inventory"]


@app.get("/api/heap/cycles")
def get_heap_cycles() -> dict:
    return get_service().get_heap_meta()


@app.get("/api/heap/pad/{cycle_id}")
def get_heap_pad(cycle_id: str) -> dict:
    try:
        return get_service().get_pad_payload(cycle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/heap/cycle/{cycle_id}/summary")
def get_heap_cycle_summary(cycle_id: str) -> dict:
    try:
        return {"cycleSummary": get_service().get_cycle_summary(cycle_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/heap/franja/{franja_id}")
def get_heap_franja(franja_id: str) -> dict:
    try:
        return get_service().get_franja_payload(franja_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/heap/compare")
def get_heap_compare(cycle_id: str = Query(...), franja_ids: Optional[str] = Query(None)) -> dict:
    ids = [item for item in franja_ids.split(",") if item] if franja_ids else None
    try:
        return get_service().get_compare_payload(cycle_id, ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/upload/preview")
async def preview_upload(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    return get_service().preview_upload(content, file.filename or "upload.csv")


@app.post("/api/upload/process")
async def process_upload(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    return get_service().process_upload(content, file.filename or "upload.csv")


@app.get("/api/template")
def download_template() -> FileResponse:
    path = get_service().ensure_template_exists()
    return FileResponse(path, filename="template_input.xlsx")


@app.get("/api/reports/excel")
def download_excel(period: Optional[str] = None) -> Response:
    content = get_service().build_excel_bytes(period)
    headers = {"Content-Disposition": "attachment; filename=balance_masas.xlsx"}
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/api/reports/pdf")
def download_pdf(period: Optional[str] = None) -> Response:
    content = get_service().build_pdf_bytes(period)
    headers = {"Content-Disposition": "attachment; filename=balance_masas.pdf"}
    return Response(content=content, media_type="application/pdf", headers=headers)


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.get("/{full_path:path}")
def serve_frontend(full_path: str) -> Response:
    index_path = FRONTEND_DIST / "index.html"
    if not FRONTEND_DIST.exists() or not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend no compilado")
    candidate = FRONTEND_DIST / full_path
    if full_path and candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index_path)
