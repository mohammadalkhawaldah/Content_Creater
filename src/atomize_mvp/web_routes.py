from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from atomize_mvp.paths import build_delivery_root
from atomize_mvp.web_jobs import create_job, get_job_status
from atomize_mvp.web_models import JobCreateResponse, JobResultsResponse, JobStatusResponse
from atomize_mvp.web_results import build_results
from atomize_mvp.web_zip import stream_zip


templates = Jinja2Templates(directory="templates")
router = APIRouter()


def _allowed_ext(name: str) -> bool:
    allowed = {".mp4", ".mov", ".wav", ".mp3", ".ogg", ".m4a", ".txt"}
    return Path(name).suffix.lower() in allowed


def _save_upload(file: UploadFile, target: Path, max_bytes: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with target.open("wb") as handle:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(status_code=413, detail="Upload too large.")
            handle.write(chunk)


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_view(request: Request, job_id: str) -> HTMLResponse:
    return templates.TemplateResponse("job.html", {"request": request, "job_id": job_id})


@router.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/jobs", response_model=JobCreateResponse)
def create_job_api(
    file: UploadFile = File(...),
    client: str = Form(...),
    title: str = Form(...),
    lang: str = Form("auto"),
    tone: str = Form("professional friendly"),
    whisper_model: str = Form("small"),
    language: str = Form("auto"),
    device: str = Form("cpu"),
    model: str = Form("gpt-4o-mini"),
    temperature: float = Form(0.3),
    max_input_chars: int = Form(120000),
    linkedin_count: int = Form(20),
    x_count: int = Form(10),
    blog_count: int = Form(5),
    ig_count: int = Form(15),
    ai_posters: bool = Form(False),
    ai_poster_count: int = Form(5),
    structured_posters: bool = Form(False),
    structured_count: int = Form(3),
    structured_theme: str = Form("bright_canva"),
    structured_premium: bool = Form(False),
) -> JobCreateResponse:
    out_root = Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    if not _allowed_ext(file.filename or ""):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    job_root = build_delivery_root(out_root, client, title)
    source_dir = job_root / "01_source"
    source_dir.mkdir(parents=True, exist_ok=True)
    target_path = source_dir / (file.filename or "upload.bin")
    max_mb = int(os.environ.get("ATOMIZE_MAX_UPLOAD_MB", "1024"))
    _save_upload(file, target_path, max_mb * 1024 * 1024)

    config = {
        "whisper_model": whisper_model,
        "language": language,
        "device": device,
        "model": model,
        "temperature": temperature,
        "max_input_chars": max_input_chars,
        "lang": lang,
        "tone": tone,
        "linkedin_count": linkedin_count,
        "x_count": x_count,
        "blog_count": blog_count,
        "ig_count": ig_count,
        "ai_posters": ai_posters,
        "ai_poster_count": ai_poster_count,
        "structured_posters": structured_posters,
        "structured_count": structured_count,
        "structured_theme": structured_theme,
        "structured_premium": structured_premium,
    }

    record = create_job(out_root, client, title, target_path, config)
    return JobCreateResponse(**record)


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    out_root = Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    record = get_job_status(out_root, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(**record)


@router.get("/api/jobs/{job_id}/logs")
def job_logs(job_id: str) -> dict:
    out_root = Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    record = get_job_status(out_root, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")
    log_path = Path(record["job_path"]) / "logs" / "atomize.log"
    if not log_path.exists():
        return {"lines": []}
    lines = log_path.read_text(encoding="utf-8").splitlines()[-200:]
    return {"lines": lines}


@router.get("/api/jobs/{job_id}/results", response_model=JobResultsResponse)
def job_results(job_id: str) -> JobResultsResponse:
    out_root = Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    record = get_job_status(out_root, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_root = Path(record["job_path"])
    results = build_results(out_root, job_root)
    return JobResultsResponse(
        id=record["id"],
        client=record["client"],
        title=record["title"],
        job_path=record["job_path"],
        **results,
    )


@router.get("/api/jobs/{job_id}/download")
def job_download(job_id: str):
    out_root = Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    record = get_job_status(out_root, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_root = Path(record["job_path"])
    final_delivery = job_root / "04_delivery" / "Final Delivery"
    target = final_delivery if final_delivery.exists() else job_root / "04_delivery"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_name = f"Atomize_{record['client']}_{record['title']}_{timestamp}.zip"
    return stream_zip(target, zip_name)
