import json
import os
from pathlib import Path

from pydantic import TypeAdapter

from atomize_mvp.llm_client import generate_repair_text, generate_text
from atomize_mvp.schemas import (
    BlogOutline,
    DraftsSchema,
    IGStory,
    LinkedinPost,
    QuickBundle,
    XThread,
)

LINKEDIN_SCHEMA = """[
  {
    "id": "LI-01",
    "hook": "string",
    "body": "string",
    "cta": "string",
    "hashtags": ["string"]
  }
]"""

X_SCHEMA = """[
  {
    "id": "X-01",
    "tweets": ["string", "string", "string"],
    "closing_cta": "string"
  }
]"""

BLOG_SCHEMA = """[
  {
    "id": "B-01",
    "title": "string",
    "audience": "string",
    "goal": "string",
    "outline": ["string", "string", "string"],
    "key_takeaways": ["string", "string", "string"]
  }
]"""

IG_SCHEMA = """[
  {
    "id": "IG-01",
    "slides": ["string", "string", "string"]
  }
]"""

QUICK_SCHEMA = """{
  "summary": "string",
  "linkedin_posts": [
    {
      "id": "LI-01",
      "hook": "string",
      "body": "string",
      "cta": "string",
      "hashtags": ["string"]
    }
  ],
  "x_threads": [
    {
      "id": "X-01",
      "tweets": ["string", "string", "string"],
      "closing_cta": "string"
    },
    {
      "id": "X-02",
      "tweets": ["string", "string", "string"],
      "closing_cta": "string"
    }
  ],
  "blog_outlines": [],
  "ig_stories": [
    {
      "id": "IG-01",
      "slides": ["string", "string", "string"]
    }
  ]
}"""


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _lang_hint(lang: str) -> str:
    if lang == "en":
        return "Output in English."
    if lang == "ar":
        return "Output in Arabic."
    return "Output in the same language as the transcript."


def _build_user_prompt(
    platform: str,
    count: int,
    tone: str,
    lang: str,
    blueprint_json: str,
    transcript_text: str,
) -> str:
    return (
        f"Platform: {platform}\n"
        f"Count: {count}\n"
        f"Tone: {tone}\n"
        f"{_lang_hint(lang)}\n"
        "Use blueprint fields heavily. Do not invent facts beyond transcript.\n"
        "Ensure items are unique and non-repetitive.\n\n"
        "Blueprint JSON:\n"
        f"{blueprint_json}\n\n"
        "Transcript:\n"
        f"{transcript_text}\n"
    )


def _validate_list(raw: str, adapter: TypeAdapter) -> list:
    data = json.loads(raw)
    return adapter.validate_python(data)


def _repair_json(raw: str, schema: str, model: str, temperature: float) -> str:
    prompt = (
        "Fix the JSON to match the schema exactly. Output JSON only.\n"
        f"Schema:\n{schema}\n\n"
        "Return EXACTLY the requested count. If short, duplicate and vary phrasing using "
        "blueprint phrases (do not invent facts).\n"
        f"Broken output:\n{raw}"
    )
    return generate_repair_text(prompt, model, temperature)


def generate_quick_bundle(
    transcript: str,
    prompt_path: Path,
    model: str,
    temperature: float,
    lang: str,
    tone: str,
    max_input_chars: int,
) -> tuple[str, QuickBundle]:
    system_prompt = prompt_path.read_text(encoding="utf-8")
    system_prompt = system_prompt.replace("{lang}", lang).replace("{tone}", tone)
    trimmed_transcript = _truncate_text(transcript, max_input_chars)
    user_prompt = (
        f"{_lang_hint(lang)}\n"
        f"Tone: {tone}\n\n"
        "Transcript:\n"
        f"{trimmed_transcript}\n"
    )
    raw = generate_text(system_prompt, user_prompt, model, temperature)
    for attempt in range(3):
        try:
            data = json.loads(raw)
            bundle = QuickBundle.model_validate(data)
            return raw, bundle
        except Exception:  # noqa: BLE001
            if attempt >= 2:
                raise
            raw = _repair_json(raw, QUICK_SCHEMA, model, temperature)
    raise RuntimeError("Failed to generate quick bundle.")


def _generate_platform(
    name: str,
    prompt_path: Path,
    schema: str,
    count: int,
    tone: str,
    lang: str,
    blueprint: dict,
    transcript: str,
    model: str,
    temperature: float,
    max_input_chars: int,
    adapter: TypeAdapter,
) -> tuple[str, list]:
    if os.environ.get("ATOMIZE_OFFLINE") == "1":
        raise RuntimeError("ATOMIZE_OFFLINE is not supported for Phase 4.")

    system_prompt = prompt_path.read_text(encoding="utf-8")
    system_prompt = system_prompt + f"\nRequested count: {count}. Output exactly {count} items."
    blueprint_json = json.dumps(blueprint, indent=2, sort_keys=True)
    trimmed_transcript = _truncate_text(transcript, max_input_chars)
    user_prompt = _build_user_prompt(
        platform=name,
        count=count,
        tone=tone,
        lang=lang,
        blueprint_json=blueprint_json,
        transcript_text=trimmed_transcript,
    )
    raw = generate_text(system_prompt, user_prompt, model, temperature)

    for attempt in range(3):
        try:
            items = _validate_list(raw, adapter)
            if len(items) != count:
                raise ValueError(
                    f"Model did not return the requested item count ({len(items)} != {count})."
                )
            return raw, items
        except Exception:  # noqa: BLE001
            if attempt >= 2:
                raise
            raw = _repair_json(raw, schema, model, temperature)
    raise RuntimeError("Failed to generate valid platform drafts.")


def generate_all_drafts(
    blueprint: dict,
    transcript: str,
    prompts_dir: Path,
    model: str,
    temperature: float,
    lang: str,
    tone: str,
    max_input_chars: int,
    linkedin_count: int,
    x_count: int,
    blog_count: int,
    ig_count: int,
) -> tuple[DraftsSchema, dict[str, str]]:
    linkedin_adapter = TypeAdapter(list[LinkedinPost])
    x_adapter = TypeAdapter(list[XThread])
    blog_adapter = TypeAdapter(list[BlogOutline])
    ig_adapter = TypeAdapter(list[IGStory])

    raw_outputs: dict[str, str] = {}

    raw, linkedin = _generate_platform(
        name="LinkedIn",
        prompt_path=prompts_dir / "linkedin.txt",
        schema=LINKEDIN_SCHEMA,
        count=linkedin_count,
        tone=tone,
        lang=lang,
        blueprint=blueprint,
        transcript=transcript,
        model=model,
        temperature=temperature,
        max_input_chars=max_input_chars,
        adapter=linkedin_adapter,
    )
    raw_outputs["raw_linkedin"] = raw

    raw, x_threads = _generate_platform(
        name="X",
        prompt_path=prompts_dir / "x_threads.txt",
        schema=X_SCHEMA,
        count=x_count,
        tone=tone,
        lang=lang,
        blueprint=blueprint,
        transcript=transcript,
        model=model,
        temperature=temperature,
        max_input_chars=max_input_chars,
        adapter=x_adapter,
    )
    raw_outputs["raw_x_threads"] = raw

    raw, blog_outlines = _generate_platform(
        name="Blog",
        prompt_path=prompts_dir / "blog_outlines.txt",
        schema=BLOG_SCHEMA,
        count=blog_count,
        tone=tone,
        lang=lang,
        blueprint=blueprint,
        transcript=transcript,
        model=model,
        temperature=temperature,
        max_input_chars=max_input_chars,
        adapter=blog_adapter,
    )
    raw_outputs["raw_blog_outlines"] = raw

    raw, ig_stories = _generate_platform(
        name="IG Stories",
        prompt_path=prompts_dir / "ig_stories.txt",
        schema=IG_SCHEMA,
        count=ig_count,
        tone=tone,
        lang=lang,
        blueprint=blueprint,
        transcript=transcript,
        model=model,
        temperature=temperature,
        max_input_chars=max_input_chars,
        adapter=ig_adapter,
    )
    raw_outputs["raw_ig_stories"] = raw

    drafts = DraftsSchema(
        linkedin_posts=linkedin,
        x_threads=x_threads,
        blog_outlines=blog_outlines,
        ig_stories=ig_stories,
    )
    return drafts, raw_outputs


def write_drafts_json(path: Path, drafts: DraftsSchema) -> None:
    path.write_text(
        json.dumps(drafts.model_dump(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
