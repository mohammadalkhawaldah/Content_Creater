from __future__ import annotations

import io
import os
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
