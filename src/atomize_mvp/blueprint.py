import json
import os
import re
import hashlib
from pathlib import Path

from atomize_mvp.llm_client import generate_blueprint, generate_repair, set_system_prompt
from atomize_mvp.schemas import ContentBlueprint

SCHEMA_TEXT = """{
  "title": "string",
  "summary": "string",
  "key_points": ["string"],
  "hooks": ["string"],
  "quotes": ["string"],
  "ctas": ["string"],
  "do_not_say": ["string"]
}"""
COUNTS_TEXT = (
    "Counts: key_points 8-12, hooks 10-20, quotes 10-20, ctas 8-12, do_not_say 5-10."
)


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_sentences(text: str) -> list[str]:
    candidates = [line.strip() for line in text.splitlines() if line.strip()]
    if len(candidates) >= 3:
        return candidates
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _ensure_count(items: list[str], min_len: int, max_len: int, fallback: list[str]) -> list[str]:
    cleaned = [item for item in items if item]
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    if not fallback:
        fallback = cleaned[:]
    if not fallback:
        fallback = [""]
    idx = 0
    while len(cleaned) < min_len:
        cleaned.append(fallback[idx % len(fallback)])
        idx += 1
    return cleaned


def _offline_blueprint(text: str, title: str, lang: str) -> ContentBlueprint:
    sentences = _extract_sentences(text)
    summary = sentences[0] if sentences else text[:120].strip()
    snippets = sentences if sentences else [text.strip()]

    key_points = [f"Point: {snippet}" for snippet in snippets[:12]]
    hooks = [f"Hook: {snippet}" for snippet in snippets[:20]]
    quotes = snippets[:20]
    ctas = [f"CTA: {snippet}" for snippet in snippets[:12]]
    do_not_say = [f"Avoid: {snippet}" for snippet in snippets[:10]]

    key_points = _ensure_count(key_points, 8, 12, key_points or snippets)
    hooks = _ensure_count(hooks, 10, 20, hooks or snippets)
    quotes = _ensure_count(quotes, 10, 20, quotes or snippets)
    ctas = _ensure_count(ctas, 8, 12, ctas or snippets)
    do_not_say = _ensure_count(do_not_say, 5, 10, do_not_say or snippets)

    return ContentBlueprint(
        title=title,
        summary=summary,
        key_points=key_points,
        hooks=hooks,
        quotes=quotes,
        ctas=ctas,
        do_not_say=do_not_say,
    )


def _build_prompt(clean_text: str, title: str, lang: str) -> str:
    if lang == "en":
        lang_hint = "Respond in English."
    elif lang == "ar":
        lang_hint = "Respond in Arabic."
    else:
        lang_hint = "Respond in the same language as the transcript."

    return (
        "You must output JSON only, no markdown, no code fences.\n"
        "The JSON must match this schema exactly:\n"
        f"{SCHEMA_TEXT}\n"
        f"{COUNTS_TEXT}\n"
        "Do not invent facts beyond the transcript.\n"
        "Quotes must be exact phrases from the transcript.\n"
        "If the transcript is short, reuse phrases rather than inventing new ones.\n"
        f"{lang_hint}\n\n"
        f"Title: {title}\n\n"
        "Transcript:\n"
        f"{clean_text}"
    )


def _extract_json_block(text: str) -> str:
    if not text:
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start : end + 1]


def generate_content_blueprint(
    clean_text: str,
    title: str,
    prompt_path: Path,
    model: str,
    temperature: float,
    max_input_chars: int,
    lang: str,
) -> tuple[str, ContentBlueprint, str]:
    trimmed_text = _truncate_text(clean_text, max_input_chars)
    input_hash = _hash_text(clean_text)

    if os.environ.get("ATOMIZE_OFFLINE") == "1":
        blueprint = _offline_blueprint(trimmed_text, title, lang)
        raw = json.dumps(blueprint.model_dump(), indent=2, sort_keys=True)
        return raw, blueprint, input_hash

    system_prompt = prompt_path.read_text(encoding="utf-8")
    set_system_prompt(system_prompt)

    user_prompt = _build_prompt(trimmed_text, title, lang)
    raw = generate_blueprint(user_prompt, model, temperature)

    for attempt in range(3):
        try:
            candidate = _extract_json_block(raw)
            data = json.loads(candidate)
            blueprint = ContentBlueprint.model_validate(data)
            return candidate, blueprint, input_hash
        except Exception as exc:  # noqa: BLE001
            if attempt >= 2:
                raise
            repair_prompt = (
                "Fix the JSON to match the schema exactly. Output JSON only.\n"
                f"Schema:\n{SCHEMA_TEXT}\n"
                f"{COUNTS_TEXT}\n"
                "Do not invent facts beyond the transcript. Quotes must be exact phrases.\n"
                "If short, reuse phrases rather than inventing.\n\n"
                f"Validation error:\n{exc}\n\n"
                f"Broken output:\n{raw}"
            )
            raw = generate_repair(repair_prompt, model, temperature)

    raise RuntimeError("Failed to generate a valid content blueprint.")
