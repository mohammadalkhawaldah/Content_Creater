import json
import os
from pathlib import Path
from multiprocessing import get_context
from concurrent.futures import ProcessPoolExecutor, as_completed

from faster_whisper import WhisperModel


def transcribe_audio_stream(
    audio_path: Path,
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
) -> tuple[int, dict]:
    whisper = WhisperModel(model, device=device)
    segments_iter, info = whisper.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
        vad_filter=vad_filter,
    )

    segment_count = 0
    last_end = None
    chunk: list[str] = []
    first = True

    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        transcript_path.open("w", encoding="utf-8") as transcript_file,
        segments_json_path.open("w", encoding="utf-8") as segments_file,
        segments_jsonl_path.open("w", encoding="utf-8") as jsonl_file,
        srt_path.open("w", encoding="utf-8") as srt_file,
    ):
        segments_file.write("[\n")
        for segment in segments_iter:
            payload = {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
            }
            segment_count += 1

            if not first:
                segments_file.write(",\n")
            first = False
            segments_file.write(json.dumps(payload, ensure_ascii=False))
            jsonl_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

            chunk.append(payload["text"])
            gap = None if last_end is None else payload["start"] - last_end
            if gap is not None and gap >= 1.0:
                transcript_file.write(" ".join(chunk).strip() + "\n\n")
                chunk = []
            elif segment_count % 4 == 0:
                transcript_file.write(" ".join(chunk).strip() + "\n\n")
                chunk = []
            last_end = payload["end"]

            start = _format_timestamp(payload["start"])
            end = _format_timestamp(payload["end"])
            srt_file.write(f"{segment_count}\n{start} --> {end}\n{payload['text']}\n\n")

        if chunk:
            transcript_file.write(" ".join(chunk).strip() + "\n")

        segments_file.write("\n]\n")

    info_dict = {
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
    }
    del whisper
    return segment_count, info_dict


def transcribe_audio_chunks(
    chunks: list[Path],
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
    segment_seconds: int,
) -> tuple[int, dict]:
    whisper = WhisperModel(model, device=device)
    segment_count = 0
    last_end = None
    chunk_text: list[str] = []
    first = True
    language_value = None
    max_end = 0.0

    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        transcript_path.open("w", encoding="utf-8") as transcript_file,
        segments_json_path.open("w", encoding="utf-8") as segments_file,
        segments_jsonl_path.open("w", encoding="utf-8") as jsonl_file,
        srt_path.open("w", encoding="utf-8") as srt_file,
    ):
        segments_file.write("[\n")
        for idx, chunk_path in enumerate(chunks):
            offset = idx * segment_seconds
            segments_iter, info = whisper.transcribe(
                str(chunk_path),
                language=None if language == "auto" else language,
                vad_filter=vad_filter,
            )
            if language_value is None:
                language_value = getattr(info, "language", None)
            for segment in segments_iter:
                payload = {
                    "start": float(segment.start) + offset,
                    "end": float(segment.end) + offset,
                    "text": segment.text.strip(),
                }
                segment_count += 1

                if not first:
                    segments_file.write(",\n")
                first = False
                segments_file.write(json.dumps(payload, ensure_ascii=False))
                jsonl_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

                chunk_text.append(payload["text"])
                gap = None if last_end is None else payload["start"] - last_end
                if gap is not None and gap >= 1.0:
                    transcript_file.write(" ".join(chunk_text).strip() + "\n\n")
                    chunk_text = []
                elif segment_count % 4 == 0:
                    transcript_file.write(" ".join(chunk_text).strip() + "\n\n")
                    chunk_text = []
                last_end = payload["end"]
                if payload["end"] > max_end:
                    max_end = payload["end"]

                start = _format_timestamp(payload["start"])
                end = _format_timestamp(payload["end"])
                srt_file.write(
                    f"{segment_count}\n{start} --> {end}\n{payload['text']}\n\n"
                )

        if chunk_text:
            transcript_file.write(" ".join(chunk_text).strip() + "\n")
        segments_file.write("\n]\n")

    info_dict = {"language": language_value, "duration": max_end}
    del whisper
    return segment_count, info_dict


def _transcribe_chunk_to_jsonl(
    chunk_path: str,
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    jsonl_path: str,
    offset_seconds: int,
) -> tuple[int, dict]:
    whisper = WhisperModel(model, device=device)
    segments_iter, info = whisper.transcribe(
        chunk_path,
        language=None if language == "auto" else language,
        vad_filter=vad_filter,
    )
    segment_count = 0
    max_end = 0.0
    with Path(jsonl_path).open("w", encoding="utf-8") as handle:
        for segment in segments_iter:
            payload = {
                "start": float(segment.start) + offset_seconds,
                "end": float(segment.end) + offset_seconds,
                "text": segment.text.strip(),
            }
            segment_count += 1
            if payload["end"] > max_end:
                max_end = payload["end"]
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    info_dict = {
        "language": getattr(info, "language", None),
        "duration": max_end,
    }
    del whisper
    return segment_count, info_dict


def _merge_jsonl_outputs(
    jsonl_paths: list[Path],
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
) -> tuple[int, float]:
    segment_count = 0
    last_end = None
    chunk_text: list[str] = []
    first = True
    max_end = 0.0
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        transcript_path.open("w", encoding="utf-8") as transcript_file,
        segments_json_path.open("w", encoding="utf-8") as segments_file,
        segments_jsonl_path.open("w", encoding="utf-8") as jsonl_file,
        srt_path.open("w", encoding="utf-8") as srt_file,
    ):
        segments_file.write("[\n")
        for path in jsonl_paths:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    payload = json.loads(line)
                    if not first:
                        segments_file.write(",\n")
                    first = False
                    segments_file.write(json.dumps(payload, ensure_ascii=False))
                    jsonl_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    segment_count += 1
                    if payload["end"] > max_end:
                        max_end = payload["end"]

                    chunk_text.append(payload["text"])
                    gap = None if last_end is None else payload["start"] - last_end
                    if gap is not None and gap >= 1.0:
                        transcript_file.write(" ".join(chunk_text).strip() + "\n\n")
                        chunk_text = []
                    elif segment_count % 4 == 0:
                        transcript_file.write(" ".join(chunk_text).strip() + "\n\n")
                        chunk_text = []
                    last_end = payload["end"]

                    start = _format_timestamp(payload["start"])
                    end = _format_timestamp(payload["end"])
                    srt_file.write(
                        f"{segment_count}\n{start} --> {end}\n{payload['text']}\n\n"
                    )

        if chunk_text:
            transcript_file.write(" ".join(chunk_text).strip() + "\n")
        segments_file.write("\n]\n")
    return segment_count, max_end


def transcribe_audio_chunks_parallel(
    chunks: list[Path],
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
    segment_seconds: int,
    max_workers: int,
) -> tuple[int, dict]:
    if not chunks:
        return 0, {"language": None, "duration": 0.0}

    jsonl_paths: list[Path] = []
    futures = []
    language_value = None
    ctx = get_context("spawn")
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as executor:
        for idx, chunk in enumerate(chunks):
            offset = idx * segment_seconds
            jsonl_path = chunk.parent / f"{chunk.stem}.jsonl"
            jsonl_paths.append(jsonl_path)
            futures.append(
                executor.submit(
                    _transcribe_chunk_to_jsonl,
                    str(chunk),
                    model,
                    language,
                    device,
                    vad_filter,
                    str(jsonl_path),
                    offset,
                )
            )
        for future in as_completed(futures):
            _, info = future.result()
            if language_value is None and info.get("language"):
                language_value = info["language"]

    jsonl_paths = sorted(jsonl_paths)
    segment_count, max_end = _merge_jsonl_outputs(
        jsonl_paths,
        transcript_path,
        segments_json_path,
        segments_jsonl_path,
        srt_path,
    )
    return segment_count, {"language": language_value, "duration": max_end}


def _transcribe_worker(
    audio_path: str,
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: str,
    segments_json_path: str,
    segments_jsonl_path: str,
    srt_path: str,
    info_path: str,
) -> None:
    segment_count, info = transcribe_audio_stream(
        audio_path=Path(audio_path),
        model=model,
        language=language,
        device=device,
        vad_filter=vad_filter,
        transcript_path=Path(transcript_path),
        segments_json_path=Path(segments_json_path),
        segments_jsonl_path=Path(segments_jsonl_path),
        srt_path=Path(srt_path),
    )
    payload = {"segments_count": segment_count, "info": info}
    Path(info_path).write_text(json.dumps(payload), encoding="utf-8")


def _transcribe_chunks_worker(
    chunks: list[str],
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: str,
    segments_json_path: str,
    segments_jsonl_path: str,
    srt_path: str,
    info_path: str,
    segment_seconds: int,
) -> None:
    segment_count, info = transcribe_audio_chunks(
        chunks=[Path(path) for path in chunks],
        model=model,
        language=language,
        device=device,
        vad_filter=vad_filter,
        transcript_path=Path(transcript_path),
        segments_json_path=Path(segments_json_path),
        segments_jsonl_path=Path(segments_jsonl_path),
        srt_path=Path(srt_path),
        segment_seconds=segment_seconds,
    )
    payload = {"segments_count": segment_count, "info": info}
    Path(info_path).write_text(json.dumps(payload), encoding="utf-8")


def transcribe_audio_subprocess(
    audio_path: Path,
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
    info_path: Path,
) -> tuple[int, dict]:
    ctx = get_context("spawn")
    proc = ctx.Process(
        target=_transcribe_worker,
        args=(
            str(audio_path),
            model,
            language,
            device,
            vad_filter,
            str(transcript_path),
            str(segments_json_path),
            str(segments_jsonl_path),
            str(srt_path),
            str(info_path),
        ),
    )
    proc.start()
    proc.join()
    if proc.exitcode != 0:
        raise RuntimeError("Transcription subprocess failed.")
    data = json.loads(info_path.read_text(encoding="utf-8"))
    return int(data.get("segments_count", 0)), data.get("info", {})


def transcribe_audio_chunks_subprocess(
    chunks: list[Path],
    model: str,
    language: str,
    device: str,
    vad_filter: bool,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
    info_path: Path,
    segment_seconds: int,
) -> tuple[int, dict]:
    ctx = get_context("spawn")
    proc = ctx.Process(
        target=_transcribe_chunks_worker,
        args=(
            [str(path) for path in chunks],
            model,
            language,
            device,
            vad_filter,
            str(transcript_path),
            str(segments_json_path),
            str(segments_jsonl_path),
            str(srt_path),
            str(info_path),
            segment_seconds,
        ),
    )
    proc.start()
    proc.join()
    if proc.exitcode != 0:
        raise RuntimeError("Transcription subprocess failed.")
    data = json.loads(info_path.read_text(encoding="utf-8"))
    return int(data.get("segments_count", 0)), data.get("info", {})


def write_segments(path: Path, segments: list[dict]) -> None:
    path.write_text(json.dumps(segments, indent=2), encoding="utf-8")


def build_transcript_text(segments: list[dict]) -> str:
    parts = []
    chunk = []
    last_end = None
    for idx, segment in enumerate(segments, start=1):
        chunk.append(segment["text"])
        gap = None if last_end is None else segment["start"] - last_end
        if gap is not None and gap >= 1.0:
            parts.append(" ".join(chunk).strip())
            parts.append("")
            chunk = []
        elif idx % 4 == 0:
            parts.append(" ".join(chunk).strip())
            parts.append("")
            chunk = []
        last_end = segment["end"]
    if chunk:
        parts.append(" ".join(chunk).strip())
    return "\n".join(parts).strip() + "\n"


def _format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(segments: list[dict]) -> str:
    lines = []
    for idx, segment in enumerate(segments, start=1):
        start = _format_timestamp(segment["start"])
        end = _format_timestamp(segment["end"])
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(segment["text"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"
