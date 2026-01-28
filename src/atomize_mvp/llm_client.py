import os

from openai import OpenAI

_SYSTEM_PROMPT = ""


def set_system_prompt(prompt: str) -> None:
    global _SYSTEM_PROMPT
    _SYSTEM_PROMPT = prompt


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
    return OpenAI(api_key=api_key)


def generate_blueprint(text: str, model: str, temperature: float) -> str:
    client = _build_client()
    messages = []
    if _SYSTEM_PROMPT:
        messages.append({"role": "system", "content": _SYSTEM_PROMPT})
    messages.append({"role": "user", "content": text})
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def generate_repair(text: str, model: str, temperature: float) -> str:
    client = _build_client()
    messages = [
        {
            "role": "system",
            "content": "You fix JSON outputs to match a required schema. Output JSON only.",
        },
        {"role": "user", "content": text},
    ]
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def generate_text(system_prompt: str, user_prompt: str, model: str, temperature: float) -> str:
    client = _build_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def generate_repair_text(text: str, model: str, temperature: float) -> str:
    return generate_repair(text, model, temperature)


def generate_image_base64(prompt: str, model: str, size: str) -> str:
    client = _build_client()
    response = client.responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "image_generation", "size": size}],
    )
    for output in response.output:
        if output.type == "image_generation_call":
            return output.result
    raise RuntimeError("Image generation failed to return image data.")
