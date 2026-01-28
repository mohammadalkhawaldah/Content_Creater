import re
from pathlib import Path

PUNCTUATION = (".", "!", "?", "،", "؛", ":")


def _normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in text.splitlines()]
    cleaned = []
    previous_blank = False
    for line in lines:
        if not line:
            if previous_blank:
                continue
            cleaned.append("")
            previous_blank = True
        else:
            cleaned.append(line)
            previous_blank = False
    return "\n".join(cleaned).strip()


def _merge_short_lines(text: str) -> str:
    lines = text.splitlines()
    merged = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue
        if not line:
            merged.append(line)
            continue
        prev = merged[-1]
        if not prev:
            merged.append(line)
            continue
        if len(line) < 40 and not prev.rstrip().endswith(PUNCTUATION):
            merged[-1] = f"{prev} {line}".strip()
        else:
            merged.append(line)
    return "\n".join(merged).strip()


def cleanup_transcript_file(source: Path, target: Path) -> None:
    text = source.read_text(encoding="utf-8")
    normalized = _normalize_whitespace(text)
    merged = _merge_short_lines(normalized)
    target.write_text(merged.strip() + "\n", encoding="utf-8")
