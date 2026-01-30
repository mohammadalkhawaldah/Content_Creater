from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from atomize_mvp.web_routes import router


def create_app(out_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="Atomize Web")
    out_root = out_root or Path(os.environ.get("ATOMIZE_OUT_ROOT", "./out")).resolve()
    os.environ["ATOMIZE_OUT_ROOT"] = str(out_root)

    app.include_router(router)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/out", StaticFiles(directory=str(out_root)), name="out")
    return app
