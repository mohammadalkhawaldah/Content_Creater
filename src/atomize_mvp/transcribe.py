import json
from pathlib import Path

from faster_whisper import WhisperModel


def transcribe_audio_stream(
    audio_path: Path,
    model: str,
    language: str,
    device: str,
    transcript_path: Path,
    segments_json_path: Path,
    segments_jsonl_path: Path,
    srt_path: Path,
) -> tuple[int, dict]:
    whisper = WhisperModel(model, device=device)
    segments_iter, info = whisper.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
        vad_filter=True,
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
