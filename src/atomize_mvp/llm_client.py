import os
import json
import logging
from datetime import datetime, timezone

from openai import OpenAI

_SYSTEM_PROMPT = ""
logger = logging.getLogger(__name__)


def set_system_prompt(prompt: str) -> None:
    global _SYSTEM_PROMPT
    _SYSTEM_PROMPT = prompt


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
    return OpenAI(api_key=api_key)


def _collect_text(node, chunks: list[str]) -> None:
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type in {"output_text", "text"} and isinstance(node.get("text"), str):
            chunks.append(node["text"])
        for value in node.values():
            _collect_text(value, chunks)
    elif isinstance(node, list):
        for item in node:
            _collect_text(item, chunks)
    else:
        node_type = getattr(node, "type", None)
        node_text = getattr(node, "text", None)
        if node_type in {"output_text", "text"} and isinstance(node_text, str):
            chunks.append(node_text)
        if hasattr(node, "__dict__"):
            for value in vars(node).values():
                _collect_text(value, chunks)


def _log_response_error(response, context: str) -> str:
    log_dir = os.environ.get("ATOMIZE_LOG_DIR")
    if not log_dir:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "response_errors.jsonl")
    payload = response
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "response": payload,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _response_text(response, context: str) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    chunks: list[str] = []
    payload = response
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    _collect_text(payload, chunks)
    merged = "".join(chunks).strip()
    if not merged:
        logger.error("Empty response text for %s", context)
        log_path = _log_response_error(payload, context)
        raise RuntimeError(
            f"Empty response text for {context}. See {log_path} for details."
        )
    return merged


def _responses_create(client: OpenAI, **kwargs):
    try:
        return client.responses.create(**kwargs)
    except TypeError as exc:
        if "response_format" not in str(exc):
            raise
        kwargs.pop("response_format", None)
        return client.responses.create(**kwargs)


def generate_blueprint(text: str, model: str, temperature: float) -> str:
    client = _build_client()
    response = _responses_create(
        client,
        model=model,
        temperature=temperature,
        instructions=_SYSTEM_PROMPT or None,
        input=[{"role": "user", "content": text}],
        response_format={"type": "json_object"},
    )
    return _response_text(response, "generate_blueprint")


def generate_repair(text: str, model: str, temperature: float) -> str:
    client = _build_client()
    response = _responses_create(
        client,
        model=model,
        temperature=temperature,
        instructions="You fix JSON outputs to match a required schema. Output JSON only.",
        input=[{"role": "user", "content": text}],
        response_format={"type": "json_object"},
    )
    return _response_text(response, "generate_repair")


def generate_text(system_prompt: str, user_prompt: str, model: str, temperature: float) -> str:
    client = _build_client()
    response = _responses_create(
        client,
        model=model,
        temperature=temperature,
        instructions=system_prompt or None,
        input=[{"role": "user", "content": user_prompt}],
        response_format={"type": "json_object"},
    )
    return _response_text(response, "generate_text")


def generate_repair_text(text: str, model: str, temperature: float) -> str:
    return generate_repair(text, model, temperature)


def generate_image_base64(prompt: str, model: str, size: str) -> str:
    client = _build_client()
    response = client.responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "image_generation", "model": "gpt-image-1-mini", "size": size}],
    )
    for output in response.output:
        if output.type == "image_generation_call":
            return output.result
    raise RuntimeError("Image generation failed to return image data.")
