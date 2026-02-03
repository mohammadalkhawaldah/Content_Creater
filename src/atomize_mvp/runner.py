import json
import logging
import os
import shutil
import gc
from datetime import datetime, timezone
from pathlib import Path

from atomize_mvp.blueprint import generate_content_blueprint
from atomize_mvp.ai_posters import export_ai_posters
from atomize_mvp.cards import render_cards
from atomize_mvp.cleanup import cleanup_transcript_file
from atomize_mvp.delivery import (
    write_blog_outlines_docx,
    write_ig_stories_docx,
    write_linkedin_docx,
    write_x_threads_docx,
)
from atomize_mvp.drafts import generate_all_drafts, write_drafts_json
from atomize_mvp.ffmpeg_utils import convert_to_mp4, ensure_ffmpeg
from atomize_mvp.finalize import finalize_delivery
from atomize_mvp.paths import build_delivery_root, delivery_tree
from atomize_mvp.structured_posters import export_structured_posters, generate_visual_blueprints
from atomize_mvp.structured_premium import export_structured_posters_premium
from atomize_mvp.render_posters import export_posters
from atomize_mvp.schemas import ContentBlueprint, DraftsSchema
from atomize_mvp.transcribe import (
    build_srt,
    build_transcript_text,
    transcribe_audio_stream,
    transcribe_audio_subprocess,
    write_segments,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _load_steps(state_path: Path) -> dict:
    return _load_json(state_path, {"steps": {}})


def _save_steps(state_path: Path, data: dict, run_path: Path | None = None) -> None:
    _save_json(state_path, data)
    if run_path is not None:
        run_data = _load_json(run_path, {})
        run_data["steps"] = data.get("steps", {})
        run_data["updated_at"] = _now_iso()
        _save_json(run_path, run_data)


def _step_done(steps: dict, name: str) -> bool:
    return steps.get("steps", {}).get(name, {}).get("status") == "done"


def _start_step(steps: dict, name: str) -> None:
    steps.setdefault("steps", {}).setdefault(name, {})
    steps["steps"][name]["status"] = "running"
    steps["steps"][name]["started_at"] = _now_iso()


def _finish_step(steps: dict, name: str, metadata: dict | None = None) -> None:
    steps.setdefault("steps", {}).setdefault(name, {})
    steps["steps"][name]["status"] = "done"
    steps["steps"][name]["finished_at"] = _now_iso()
    if metadata:
        steps["steps"][name]["metadata"] = metadata


def _fail_step(steps: dict, name: str, error: str) -> None:
    steps.setdefault("steps", {}).setdefault(name, {})
    steps["steps"][name]["status"] = "failed"
    steps["steps"][name]["finished_at"] = _now_iso()
    steps["steps"][name]["error"] = error


def _ensure_dirs(tree: dict) -> None:
    for key, path in tree.items():
        if key == "root":
            continue
        path.mkdir(parents=True, exist_ok=True)


def _cleanup_memory(label: str) -> None:
    logger.info("Cleaning up memory after %s", label)
    try:
        import psutil  # type: ignore

        rss = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info("RSS memory after %s: %.1f MB", label, rss)
    except Exception:
        pass
    gc.collect()
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return


def _outputs_exist(paths: list[Path]) -> bool:
    return all(path.exists() for path in paths)


def _should_skip(steps: dict, name: str, outputs: list[Path], force: bool) -> bool:
    return _step_done(steps, name) and _outputs_exist(outputs) and not force


def _write_txt_input_outputs(text: str, tree: dict) -> None:
    transcript_path = tree["transcripts"] / "transcript.txt"
    transcript_path.write_text(text, encoding="utf-8")

    segments = [{"start": 0.0, "end": 0.0, "text": text}]
    write_segments(tree["transcripts"] / "segments.json", segments)

    srt_content = build_srt(segments)
    (tree["transcripts"] / "transcript.srt").write_text(srt_content, encoding="utf-8")


def _stage_source(input_path: Path, tree: dict) -> Path:
    dest = tree["source"] / input_path.name
    if not dest.exists():
        shutil.copy2(input_path, dest)
    return dest


def _snapshot_posters(tree: dict) -> None:
    delivery_dir = tree["delivery"]
    if not delivery_dir.exists():
        return
    poster_files = []
    for folder in delivery_dir.glob("Posters*"):
        if (
            folder.is_dir()
            and folder.name not in {"Posters_All", "Posters_AI"}
        ):
            poster_files.extend(folder.rglob("*.png"))
    if not poster_files:
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_root = delivery_dir / "Posters_All" / stamp
    for path in poster_files:
        rel = path.relative_to(delivery_dir)
        target = snapshot_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def run_pipeline(
    input_path: Path,
    client: str,
    title: str,
    out_root: Path,
    force: bool,
    whisper_model: str,
    language: str,
    device: str,
    model: str,
    temperature: float,
    max_input_chars: int,
    lang: str,
    tone: str,
    linkedin_count: int,
    x_count: int,
    blog_count: int,
    ig_count: int,
    ai_posters: bool,
    ai_poster_count: int,
    structured_posters: bool,
    structured_count: int,
    structured_theme: str,
    structured_only: bool,
    structured_premium: bool,
) -> None:
    root = build_delivery_root(out_root, client, title)
    tree = delivery_tree(root)
    state_file = tree["state"] / "steps.json"
    run_file = tree["state"] / "run.json"

    _ensure_dirs(tree)
    steps = _load_steps(state_file)

    if not _step_done(steps, "init") or force:
        logger.info("Running step init")
        _start_step(steps, "init")
        meta = {
            "client": client,
            "title": title,
            "input": str(input_path),
            "created_at": _now_iso(),
            "phase": "phase_8",
        }
        _save_json(run_file, meta)
        _finish_step(steps, "init")
        _save_steps(state_file, steps, run_file)
        logger.info("Step init complete")

    if not _should_skip(steps, "stage_source", [tree["source"] / input_path.name], force):
        logger.info("Running step stage_source")
        _start_step(steps, "stage_source")
        staged = _stage_source(input_path, tree)
        _finish_step(steps, "stage_source", {"staged_path": str(staged)})
        _save_steps(state_file, steps, run_file)
        logger.info("Step stage_source complete")

    if input_path.suffix.lower() == ".txt":
        transcript_outputs = [
            tree["transcripts"] / "transcript.txt",
            tree["transcripts"] / "segments.json",
            tree["transcripts"] / "transcript.jsonl",
            tree["transcripts"] / "transcript.srt",
        ]
        if not _should_skip(steps, "transcribe", transcript_outputs, force):
            logger.info("Running step transcribe (txt input)")
            _start_step(steps, "transcribe")
            try:
                text = input_path.read_text(encoding="utf-8")
                _write_txt_input_outputs(text, tree)
                (tree["transcripts"] / "transcript.jsonl").write_text(
                    json.dumps({"start": 0.0, "end": 0.0, "text": text}, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
                _finish_step(
                    steps,
                    "transcribe",
                    {
                        "model": "none",
                        "language": "n/a",
                        "device": "n/a",
                        "segments_count": 1,
                        "input_duration": 0.0,
                    },
                )
                _save_steps(state_file, steps, run_file)
                logger.info("Step transcribe complete")
            except Exception as exc:  # noqa: BLE001
                _fail_step(steps, "transcribe", str(exc))
                _save_steps(state_file, steps, run_file)
                raise

        cleanup_output = [tree["transcripts"] / "clean_transcript.txt"]
        if not _should_skip(steps, "cleanup_transcript", cleanup_output, force):
            logger.info("Running step cleanup_transcript")
            _start_step(steps, "cleanup_transcript")
            try:
                cleanup_transcript_file(
                    tree["transcripts"] / "transcript.txt",
                    tree["transcripts"] / "clean_transcript.txt",
                )
                _finish_step(steps, "cleanup_transcript")
                _save_steps(state_file, steps, run_file)
                logger.info("Step cleanup_transcript complete")
            except Exception as exc:  # noqa: BLE001
                _fail_step(steps, "cleanup_transcript", str(exc))
                _save_steps(state_file, steps, run_file)
                raise
    else:
        audio_path = tree["transcripts"] / "audio.mp4"
        if not _should_skip(steps, "prepare_audio", [audio_path], force):
            logger.info("Running step prepare_audio")
            _start_step(steps, "prepare_audio")
            try:
                ensure_ffmpeg()
                convert_to_mp4(input_path, audio_path)
                _finish_step(steps, "prepare_audio", {"audio_path": str(audio_path)})
                _save_steps(state_file, steps, run_file)
                logger.info("Step prepare_audio complete")
            except Exception as exc:  # noqa: BLE001
                _fail_step(steps, "prepare_audio", str(exc))
                _save_steps(state_file, steps, run_file)
                raise

        transcript_outputs = [
            tree["transcripts"] / "transcript.txt",
            tree["transcripts"] / "segments.json",
            tree["transcripts"] / "transcript.jsonl",
            tree["transcripts"] / "transcript.srt",
        ]
        if not _should_skip(steps, "transcribe", transcript_outputs, force):
            logger.info("Running step transcribe")
            _start_step(steps, "transcribe")
            try:
                info_path = tree["transcripts"] / "transcribe_info.json"
                use_subprocess = os.environ.get("ATOMIZE_TRANSCRIBE_SUBPROCESS") == "1"
                if os.environ.get("RENDER"):
                    use_subprocess = True
                vad_env = os.environ.get("ATOMIZE_WHISPER_VAD")
                if vad_env is None:
                    vad_filter = False if os.environ.get("RENDER") else True
                else:
                    vad_filter = vad_env.strip().lower() in {"1", "true", "yes", "on"}
                if use_subprocess:
                    segment_count, info = transcribe_audio_subprocess(
                        audio_path=audio_path,
                        model=whisper_model,
                        language=language,
                        device=device,
                        vad_filter=vad_filter,
                        transcript_path=tree["transcripts"] / "transcript.txt",
                        segments_json_path=tree["transcripts"] / "segments.json",
                        segments_jsonl_path=tree["transcripts"] / "transcript.jsonl",
                        srt_path=tree["transcripts"] / "transcript.srt",
                        info_path=info_path,
                    )
                else:
                    segment_count, info = transcribe_audio_stream(
                        audio_path=audio_path,
                        model=whisper_model,
                        language=language,
                        device=device,
                        vad_filter=vad_filter,
                        transcript_path=tree["transcripts"] / "transcript.txt",
                        segments_json_path=tree["transcripts"] / "segments.json",
                        segments_jsonl_path=tree["transcripts"] / "transcript.jsonl",
                        srt_path=tree["transcripts"] / "transcript.srt",
                    )

                metadata = {
                    "model": whisper_model,
                    "language": info.get("language", language),
                    "device": device,
                    "segments_count": segment_count,
                }
                if info.get("duration") is not None:
                    metadata["input_duration"] = info["duration"]

                _finish_step(steps, "transcribe", metadata)
                _save_steps(state_file, steps, run_file)
                logger.info("Step transcribe complete")
                _cleanup_memory("transcribe")
            except Exception as exc:  # noqa: BLE001
                _fail_step(steps, "transcribe", str(exc))
                _save_steps(state_file, steps, run_file)
                raise

        cleanup_output = [tree["transcripts"] / "clean_transcript.txt"]
        if not _should_skip(steps, "cleanup_transcript", cleanup_output, force):
            logger.info("Running step cleanup_transcript")
            _start_step(steps, "cleanup_transcript")
            try:
                cleanup_transcript_file(
                    tree["transcripts"] / "transcript.txt",
                    tree["transcripts"] / "clean_transcript.txt",
                )
                _finish_step(steps, "cleanup_transcript")
                _save_steps(state_file, steps, run_file)
                logger.info("Step cleanup_transcript complete")
            except Exception as exc:  # noqa: BLE001
                _fail_step(steps, "cleanup_transcript", str(exc))
                _save_steps(state_file, steps, run_file)
                raise

    blueprint_dir = tree["content"] / "blueprint"
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    blueprint_json = blueprint_dir / "content_blueprint.json"
    blueprint_raw = blueprint_dir / "content_blueprint.raw.txt"
    blueprint_outputs = [blueprint_json, blueprint_raw]

    if not _should_skip(steps, "blueprint", blueprint_outputs, force):
        logger.info("Running step blueprint")
        _start_step(steps, "blueprint")
        try:
            clean_path = tree["transcripts"] / "clean_transcript.txt"
            clean_text = clean_path.read_text(encoding="utf-8")
            raw, blueprint, input_hash = generate_content_blueprint(
                clean_text=clean_text,
                title=title,
                prompt_path=Path(__file__).parent / "prompts" / "content_blueprint.txt",
                model=model,
                temperature=temperature,
                max_input_chars=max_input_chars,
                lang=lang,
            )
            blueprint_raw.write_text(raw, encoding="utf-8")
            blueprint_json.write_text(
                json.dumps(blueprint.model_dump(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            _finish_step(
                steps,
                "blueprint",
                {
                    "model": model,
                    "temperature": temperature,
                    "lang": lang,
                    "input_hash": input_hash,
                    "output": str(blueprint_json),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step blueprint complete")
        except Exception as exc:  # noqa: BLE001
            if "raw" in locals():
                blueprint_raw.write_text(raw, encoding="utf-8")
            _fail_step(steps, "blueprint", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    drafts_dir = tree["content"] / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    drafts_json = drafts_dir / "drafts.json"
    raw_linkedin = drafts_dir / "raw_linkedin.txt"
    raw_x_threads = drafts_dir / "raw_x_threads.txt"
    raw_blog_outlines = drafts_dir / "raw_blog_outlines.txt"
    raw_ig_stories = drafts_dir / "raw_ig_stories.txt"

    drafts_outputs = [drafts_json]

    if not _should_skip(steps, "generate_drafts", drafts_outputs, force):
        logger.info("Running step generate_drafts")
        _start_step(steps, "generate_drafts")
        try:
            clean_path = tree["transcripts"] / "clean_transcript.txt"
            clean_text = clean_path.read_text(encoding="utf-8")
            blueprint_data = json.loads(blueprint_json.read_text(encoding="utf-8"))

            drafts, raw_outputs = generate_all_drafts(
                blueprint=blueprint_data,
                transcript=clean_text,
                prompts_dir=Path(__file__).parent / "prompts",
                model=model,
                temperature=temperature,
                lang=lang,
                tone=tone,
                max_input_chars=max_input_chars,
                linkedin_count=linkedin_count,
                x_count=x_count,
                blog_count=blog_count,
                ig_count=ig_count,
            )

            raw_linkedin.write_text(raw_outputs["raw_linkedin"], encoding="utf-8")
            raw_x_threads.write_text(raw_outputs["raw_x_threads"], encoding="utf-8")
            raw_blog_outlines.write_text(raw_outputs["raw_blog_outlines"], encoding="utf-8")
            raw_ig_stories.write_text(raw_outputs["raw_ig_stories"], encoding="utf-8")

            write_drafts_json(drafts_json, drafts)

            delivery_dir = tree["delivery"] / "Platform Ready"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            write_linkedin_docx(delivery_dir / "LinkedIn_Posts.docx", drafts)
            write_x_threads_docx(delivery_dir / "X_Threads.docx", drafts)
            write_blog_outlines_docx(delivery_dir / "Blog_Outlines.docx", drafts)
            write_ig_stories_docx(delivery_dir / "IG_Stories.docx", drafts)

            _finish_step(
                steps,
                "generate_drafts",
                {
                    "model": model,
                    "temperature": temperature,
                    "lang": lang,
                    "tone": tone,
                    "counts": {
                        "linkedin": linkedin_count,
                        "x": x_count,
                        "blog": blog_count,
                        "ig": ig_count,
                    },
                    "output": str(drafts_json),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step generate_drafts complete")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "generate_drafts", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    finalize_outputs = [
        tree["delivery"] / f"Content Library - {client} - {title}.docx",
        tree["delivery"] / f"Hooks & Quotes - {client} - {title}.docx",
        tree["delivery"] / f"README - Start Here - {client} - {title}.docx",
    ]

    if not _should_skip(steps, "finalize_delivery", finalize_outputs, force):
        logger.info("Running step finalize_delivery")
        _start_step(steps, "finalize_delivery")
        try:
            drafts_data = json.loads(drafts_json.read_text(encoding="utf-8"))
            blueprint_data = json.loads(blueprint_json.read_text(encoding="utf-8"))
            outputs = finalize_delivery(
                job_root=root,
                drafts=DraftsSchema.model_validate(drafts_data),
                blueprint=ContentBlueprint.model_validate(blueprint_data),
                client=client,
                title=title,
                lang=lang,
                tone=tone,
                include_schedule=True,
            )
            output_paths = [
                str(outputs.content_library),
                str(outputs.hooks_quotes),
                str(outputs.readme),
            ]
            if outputs.schedule:
                output_paths.append(str(outputs.schedule))
            _finish_step(
                steps,
                "finalize_delivery",
                {
                    "output_paths": output_paths,
                    "counts": {
                        "linkedin": len(drafts_data.get("linkedin_posts", [])),
                        "x": len(drafts_data.get("x_threads", [])),
                        "blog": len(drafts_data.get("blog_outlines", [])),
                        "ig": len(drafts_data.get("ig_stories", [])),
                    },
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step finalize_delivery complete")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "finalize_delivery", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    cards_outputs = [
        tree["delivery"] / "Cards" / "index.html",
        tree["delivery"] / "Cards" / "cards.css",
        tree["delivery"] / "Cards" / "cards.json",
    ]
    if not _should_skip(steps, "render_cards", cards_outputs, force):
        logger.info("Running step render_cards")
        _start_step(steps, "render_cards")
        try:
            drafts_data = json.loads(drafts_json.read_text(encoding="utf-8"))
            outputs = render_cards(
                job_root=root,
                drafts=DraftsSchema.model_validate(drafts_data),
                client=client,
                title=title,
            )
            _finish_step(
                steps,
                "render_cards",
                {"output_paths": [str(path) for path in outputs]},
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step render_cards complete")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "render_cards", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    posters_root = tree["delivery"] / "Posters"
    posters_outputs = [posters_root]
    if not _should_skip(steps, "export_posters", posters_outputs, force):
        logger.info("Running step export_posters")
        _start_step(steps, "export_posters")
        try:
            cards_dir = tree["delivery"] / "Cards"
            outputs = export_posters(cards_dir=cards_dir, posters_root=posters_root)
            _finish_step(
                steps,
                "export_posters",
                {
                    "poster_count": len(outputs),
                    "output_path": str(posters_root),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step export_posters complete")
            _cleanup_memory("export_posters")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "export_posters", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    ai_posters_root = tree["delivery"] / "Posters_AI"
    ai_posters_outputs = [ai_posters_root]
    if ai_posters and not _should_skip(steps, "export_ai_posters", ai_posters_outputs, force):
        logger.info("Running step export_ai_posters")
        _start_step(steps, "export_ai_posters")
        try:
            cards_dir = tree["delivery"] / "Cards"
            outputs = export_ai_posters(
                cards_dir=cards_dir,
                posters_root=ai_posters_root,
                model=model,
                count=ai_poster_count,
            )
            _finish_step(
                steps,
                "export_ai_posters",
                {
                    "ai_poster_count": len(outputs),
                    "output_path": str(ai_posters_root),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step export_ai_posters complete")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "export_ai_posters", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    structured_root = tree["delivery"] / "Posters_Structured"
    blueprints_dir = tree["content"] / "visual_blueprints"
    structured_outputs = [structured_root]
    if structured_posters and not _should_skip(
        steps, "export_structured_posters", structured_outputs, force
    ):
        logger.info("Running step export_structured_posters")
        _start_step(steps, "export_structured_posters")
        try:
            cards_dir = tree["delivery"] / "Cards"
            blueprints = generate_visual_blueprints(
                cards_dir=cards_dir,
                output_dir=blueprints_dir,
                count=structured_count,
            )
            outputs = export_structured_posters(
                cards_dir=cards_dir,
                blueprints=blueprints,
                posters_root=structured_root,
                model=model,
            )
            _finish_step(
                steps,
                "export_structured_posters",
                {
                    "structured_count": len(outputs),
                    "output_path": str(structured_root),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step export_structured_posters complete")
            _cleanup_memory("export_structured_posters")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "export_structured_posters", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    premium_root = tree["delivery"] / "Posters_Structured_Premium"
    premium_outputs = [premium_root]
    if structured_only and not (tree["content"] / "visual_blueprints").exists():
        raise FileNotFoundError("visual_blueprints not found. Run structured posters first.")

    if (structured_posters or structured_premium or structured_only) and not _should_skip(
        steps, "export_structured_posters_premium", premium_outputs, force
    ):
        logger.info("Running step export_structured_posters_premium")
        _start_step(steps, "export_structured_posters_premium")
        try:
            cards_dir = tree["delivery"] / "Cards"
            blueprints_dir = tree["content"] / "visual_blueprints"
            outputs = export_structured_posters_premium(
                cards_dir=cards_dir,
                blueprints_dir=blueprints_dir,
                posters_root=premium_root,
                theme_name=structured_theme,
                model=model,
                font_path=os.environ.get("ATOMIZE_FONT_PATH"),
            )
            _finish_step(
                steps,
                "export_structured_posters_premium",
                {
                    "theme": structured_theme,
                    "output_path": str(premium_root),
                    "poster_count": len(outputs),
                },
            )
            _save_steps(state_file, steps, run_file)
            logger.info("Step export_structured_posters_premium complete")
            _cleanup_memory("export_structured_posters_premium")
        except Exception as exc:  # noqa: BLE001
            _fail_step(steps, "export_structured_posters_premium", str(exc))
            _save_steps(state_file, steps, run_file)
            raise

    _snapshot_posters(tree)
    _cleanup_memory("pipeline")
