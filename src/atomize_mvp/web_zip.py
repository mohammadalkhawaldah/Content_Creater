from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
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
    shutil.copytree(final_delivery, staging_root, dirs_exist_ok=True)

    posters_parent = staging_root / "Posters"
    for folder in delivery_root.glob("Posters*"):
        if not folder.is_dir():
            continue
        if folder.name == "Posters_All":
            continue
        target = posters_parent / folder.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(folder, target, dirs_exist_ok=True)

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
