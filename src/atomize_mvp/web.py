from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

from atomize_mvp.web_app import create_app


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="atomize_mvp web")
    parser.add_argument("--host", default=os.environ.get("ATOMIZE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ATOMIZE_PORT", "8000")))
    parser.add_argument("--out", default=os.environ.get("ATOMIZE_OUT_ROOT", "./out"))
    args = parser.parse_args(argv)

    out_root = Path(args.out).resolve()
    os.environ["ATOMIZE_OUT_ROOT"] = str(out_root)
    app = create_app(out_root)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
