from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
import json
from datetime import datetime, timezone
from pathlib import Path



def _zip_folder(folder: Path) -> Path:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp.close()
    zip_path = Path(temp.name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(folder))
    return zip_path


def stream_zip(folder: Path, zip_name: str):
    from fastapi.responses import StreamingResponse

    zip_path = _zip_folder(folder)

    def iterfile():
        with open(zip_path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        os.unlink(zip_path)

    headers = {"Content-Disposition": f'attachment; filename="{zip_name}"'}
    return StreamingResponse(iterfile(), media_type="application/zip", headers=headers)


def stream_delivery_zip(job_root: Path, zip_name: str):
    from fastapi.responses import StreamingResponse

    delivery_root = job_root / "04_delivery"
    final_delivery = delivery_root / "Final Delivery"
    if not final_delivery.exists():
        return stream_zip(delivery_root, zip_name)

    temp_dir = tempfile.TemporaryDirectory()
    staging_root = Path(temp_dir.name) / "Final Delivery"
    _copytree_filtered(final_delivery, staging_root, _started_at(job_root))

    posters_parent = staging_root / "Posters"
    started_at = _started_at(job_root)
    for folder in delivery_root.glob("Posters*"):
        if not folder.is_dir():
            continue
        if folder.name in {"Posters_All", "Posters_AI"}:
            continue
        target = posters_parent / folder.name
        target.parent.mkdir(parents=True, exist_ok=True)
        _copytree_filtered(folder, target, started_at)

    zip_path = _zip_folder(staging_root)

    def iterfile():
        with open(zip_path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        os.unlink(zip_path)
        temp_dir.cleanup()

    headers = {"Content-Disposition": f'attachment; filename=\"{zip_name}\"'}
    return StreamingResponse(iterfile(), media_type="application/zip", headers=headers)


def _started_at(job_root: Path) -> datetime | None:
    marker = job_root / ".atomize" / "web_job.json"
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        value = data.get("started_at")
    except json.JSONDecodeError:
        return None
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _copytree_filtered(source: Path, dest: Path, started_at: datetime | None) -> None:
    if not source.exists():
        return
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        if started_at is not None:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime < started_at:
                continue
        rel = path.relative_to(source)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
