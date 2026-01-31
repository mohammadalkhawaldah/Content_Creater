from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from atomize_mvp.logging_utils import configure_logging
from atomize_mvp.paths import build_delivery_root, delivery_tree
from atomize_mvp.runner import run_pipeline


REGISTRY_DIR = ".atomize_web"
REGISTRY_FILE = "jobs.json"


def _registry_path(out_root: Path) -> Path:
    path = out_root / REGISTRY_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path / REGISTRY_FILE


def load_registry(out_root: Path) -> list[dict]:
    path = _registry_path(out_root)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(out_root: Path, records: list[dict]) -> None:
    path = _registry_path(out_root)
    path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")


def append_registry(out_root: Path, record: dict) -> None:
    records = load_registry(out_root)
    records.append(record)
    save_registry(out_root, records)


def _update_registry(out_root: Path, job_id: str, fields: dict) -> None:
    records = load_registry(out_root)
    for record in records:
        if record.get("id") == job_id:
            record.update(fields)
            break
    save_registry(out_root, records)


def _read_steps_status(job_root: Path) -> dict:
    steps_path = job_root / ".atomize" / "steps.json"
    if not steps_path.exists():
        return {}
    try:
        return json.loads(steps_path.read_text(encoding="utf-8")).get("steps", {})
    except json.JSONDecodeError:
        return {}


def _infer_progress(steps: dict) -> tuple[str | None, int, bool, bool]:
    order = [
        "init",
        "stage_source",
        "prepare_audio",
        "transcribe",
        "cleanup_transcript",
        "blueprint",
        "generate_drafts",
        "finalize_delivery",
        "render_cards",
        "export_posters",
        "export_structured_posters",
        "export_structured_posters_premium",
        "export_infographic_posters",
    ]
    completed = 0
    current = None
    has_failed = False
    has_running = False
    for step in order:
        status = steps.get(step, {}).get("status")
        if status == "done":
            completed += 1
        elif status == "running":
            current = step
            has_running = True
            break
        elif status == "failed":
            has_failed = True
    percent = int((completed / max(len(order), 1)) * 100)
    return current, percent, has_running, has_failed


def get_job_status(out_root: Path, job_id: str) -> dict | None:
    records = load_registry(out_root)
    for record in records:
        if record.get("id") == job_id:
            job_root = Path(record["job_path"])
            steps = _read_steps_status(job_root)
            current_step, percent, has_running, has_failed = _infer_progress(steps)
            record = {**record}
            record["current_step"] = current_step
            record["percent"] = percent
            if record.get("status") == "running":
                if has_failed:
                    record["status"] = "failed"
                    _update_registry(out_root, job_id, {"status": "failed"})
                elif not has_running and percent == 100:
                    record["status"] = "succeeded"
                    _update_registry(out_root, job_id, {"status": "succeeded"})
            return record
    return None


def create_job(
    out_root: Path,
    client: str,
    title: str,
    input_path: Path,
    config: dict[str, Any],
) -> dict:
    job_id = str(uuid.uuid4())
    job_root = build_delivery_root(out_root, client, title)
    tree = delivery_tree(job_root)
    for path in tree.values():
        if path == job_root:
            continue
        path.mkdir(parents=True, exist_ok=True)

    record = {
        "id": job_id,
        "client": client,
        "title": title,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "queued",
        "job_path": str(job_root),
        "input_path": str(input_path),
    }
    append_registry(out_root, record)
    thread = threading.Thread(
        target=_run_job, args=(out_root, job_id, config), daemon=True
    )
    thread.start()
    return record


def _run_job(out_root: Path, job_id: str, config: dict[str, Any]) -> None:
    status = get_job_status(out_root, job_id)
    if not status:
        return
    _update_registry(out_root, job_id, {"status": "running"})

    job_root = Path(status["job_path"])
    configure_logging(out_root, status["client"], status["title"], "INFO")
    try:
        run_pipeline(
            input_path=Path(status["input_path"]),
            client=status["client"],
            title=status["title"],
            out_root=out_root,
            force=True,
            whisper_model=config["whisper_model"],
            language=config["language"],
            device=config["device"],
            model=config["model"],
            temperature=config["temperature"],
            max_input_chars=config["max_input_chars"],
            lang=config["lang"],
            tone=config["tone"],
            linkedin_count=config["linkedin_count"],
            x_count=config["x_count"],
            blog_count=config["blog_count"],
            ig_count=config["ig_count"],
            ai_posters=config["ai_posters"],
            ai_poster_count=config["ai_poster_count"],
            structured_posters=config["structured_posters"],
            structured_count=config["structured_count"],
            structured_theme=config["structured_theme"],
            structured_only=False,
            structured_premium=config["structured_premium"],
        )
        _update_registry(out_root, job_id, {"status": "succeeded"})
    except Exception as exc:  # noqa: BLE001
        _update_registry(out_root, job_id, {"status": "failed", "error": str(exc)})
