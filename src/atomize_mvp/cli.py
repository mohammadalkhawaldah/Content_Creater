import argparse
import sys
import os
from pathlib import Path

from dotenv import load_dotenv

from atomize_mvp.logging_utils import configure_logging
from atomize_mvp.runner import run_pipeline
from atomize_mvp.web import main as web_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atomize_mvp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run Atomize MVP pipeline")
    run_parser.add_argument("--input", required=True, help="Path to input audio/video file")
    run_parser.add_argument("--client", required=True, help="Client name")
    run_parser.add_argument("--title", required=True, help="Project title")
    run_parser.add_argument("--out", required=True, help="Output folder root")
    run_parser.add_argument("--force", action="store_true", help="Re-run completed steps")
    run_parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    default_whisper = os.environ.get("ATOMIZE_WHISPER_MODEL")
    if not default_whisper:
        default_whisper = "base" if os.environ.get("RENDER") else "small"
    run_parser.add_argument(
        "--whisper-model",
        default=default_whisper,
        help=f"faster-whisper model (default: {default_whisper})",
    )
    run_parser.add_argument(
        "--language", default="auto", help="Language code or auto (default: auto)"
    )
    run_parser.add_argument("--device", default="cpu", help="Device (default: cpu)")
    run_parser.add_argument("--model", default="gpt-4o-mini", help="LLM model (default: gpt-4o-mini)")
    run_parser.add_argument("--temperature", default=0.3, type=float, help="LLM temperature")
    run_parser.add_argument(
        "--max-input-chars",
        default=120000,
        type=int,
        help="Max characters to send to the model",
    )
    run_parser.add_argument(
        "--lang",
        default="auto",
        choices=["auto", "en", "ar"],
        help="Blueprint language (auto, en, ar)",
    )
    run_parser.add_argument(
        "--tone",
        default="professional friendly",
        help="Drafts tone (default: professional friendly)",
    )
    run_parser.add_argument("--linkedin-count", default=2, type=int, help="LinkedIn posts count")
    run_parser.add_argument("--x-count", default=2, type=int, help="X threads count")
    run_parser.add_argument("--blog-count", default=2, type=int, help="Blog outlines count")
    run_parser.add_argument("--ig-count", default=2, type=int, help="IG stories count")
    run_parser.add_argument(
        "--ai-posters",
        action="store_true",
        help="Enable AI background posters export (default: false)",
    )
    run_parser.add_argument(
        "--ai-poster-count",
        default=2,
        type=int,
        help="Number of AI posters to generate (default: 2)",
    )
    run_parser.add_argument(
        "--structured-posters",
        action="store_true",
        help="Enable structured posters export (default: false)",
    )
    run_parser.add_argument(
        "--structured-count",
        default=2,
        type=int,
        help="Number of structured posters to generate (default: 2)",
    )
    run_parser.add_argument(
        "--structured-theme",
        default="bright_canva",
        help="Structured poster theme (default: bright_canva)",
    )
    run_parser.add_argument(
        "--structured-only",
        action="store_true",
        help="Only render premium structured posters using existing blueprints",
    )
    run_parser.add_argument(
        "--structured-premium",
        action="store_true",
        help="Enable premium structured posters export",
    )

    web_parser = subparsers.add_parser("web", help="Start Atomize web server")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    web_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    web_parser.add_argument("--out", default="./out", help="Output folder root")

    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        input_path = Path(args.input).expanduser()
        out_root = Path(args.out).expanduser()

        if not input_path.exists():
            print(f"Input not found: {input_path}", file=sys.stderr)
            sys.exit(2)

        configure_logging(out_root, args.client, args.title, args.log_level)
        run_pipeline(
            input_path=input_path,
            client=args.client,
            title=args.title,
            out_root=out_root,
            force=args.force,
            whisper_model=args.whisper_model,
            language=args.language,
            device=args.device,
            model=args.model,
            temperature=args.temperature,
            max_input_chars=args.max_input_chars,
            lang=args.lang,
            tone=args.tone,
            linkedin_count=args.linkedin_count,
            x_count=args.x_count,
            blog_count=args.blog_count,
            ig_count=args.ig_count,
            ai_posters=args.ai_posters,
            ai_poster_count=args.ai_poster_count,
            structured_posters=args.structured_posters,
            structured_count=args.structured_count,
            structured_theme=args.structured_theme,
            structured_only=args.structured_only,
            structured_premium=args.structured_premium,
        )
    elif args.command == "web":
        out_root = Path(args.out).expanduser()
        web_main(
            [
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--out",
                str(out_root),
            ]
        )
