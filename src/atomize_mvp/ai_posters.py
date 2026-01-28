import base64
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from atomize_mvp.llm_client import generate_image_base64

PLATFORM_FOLDERS = {
    "LinkedIn": "LinkedIn",
    "X / Twitter": "X",
    "Instagram Stories": "Instagram",
}

BASE_STYLE = (
    "modern, clean, professional, tech and AI drone theme, minimal infographic look, "
    "blue and teal color palette, soft gradients, high contrast center space, no text"
)


def build_background_prompt(card: dict) -> str:
    topic = card.get("title") or "technology"
    return (
        f"Modern flat illustration about {topic}, {BASE_STYLE}. "
        "High detail, crisp shapes."
    )


def ai_poster_output_path(posters_root: Path, platform: str, content_id: str) -> Path:
    folder = PLATFORM_FOLDERS.get(platform, "Other")
    return posters_root / folder / f"{content_id}.png"


def select_hero_cards(cards: list[dict], count: int) -> list[dict]:
    heroes = [card for card in cards if card.get("hero") is True]
    if heroes:
        return heroes[:count]
    return cards[:count]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ["arial.ttf", "segoeui.ttf"]:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_lines(text: str, width: int) -> list[str]:
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, width=width) or [""])
    return [line for line in lines if line.strip()]


def _compose_poster(background: Image.Image, card: dict) -> Image.Image:
    canvas = background.resize((1080, 1080)).convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 90))
    canvas = Image.alpha_composite(canvas, overlay)

    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(56)
    body_font = _load_font(36)
    cta_font = _load_font(28)

    margin = 70
    y = margin
    title = card.get("title", "")
    body = card.get("content", "")
    cta = card.get("cta", "")

    title_lines = _wrap_lines(title, width=22)[:2]
    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255, 255))
        y += title_font.size + 8

    body_lines = _wrap_lines(body, width=32)[:3]
    for line in body_lines:
        draw.text((margin, y), f"• {line}", font=body_font, fill=(235, 235, 235, 255))
        y += body_font.size + 6

    if cta:
        draw.text(
            (margin, 1080 - margin - 40),
            cta[:120],
            font=cta_font,
            fill=(255, 255, 255, 255),
        )

    return canvas.convert("RGB")


def export_ai_posters(
    cards_dir: Path,
    posters_root: Path,
    model: str,
    count: int,
) -> list[Path]:
    cards_json = cards_dir / "cards.json"
    if not cards_json.exists():
        raise FileNotFoundError("cards.json not found. Run render_cards first.")

    cards = json.loads(cards_json.read_text(encoding="utf-8"))
    selected = select_hero_cards(cards, count)
    outputs: list[Path] = []

    backgrounds_dir = posters_root / "_backgrounds"
    backgrounds_dir.mkdir(parents=True, exist_ok=True)

    for card in selected:
        content_id = card["id"]
        platform = card["platform"]
        prompt = build_background_prompt(card)

        image_b64 = generate_image_base64(prompt, model=model, size="1024x1024")
        background_path = backgrounds_dir / f"{content_id}.png"
        background_path.write_bytes(base64.b64decode(image_b64))

        background = Image.open(background_path)
        poster = _compose_poster(background, card)

        output_path = ai_poster_output_path(posters_root, platform, content_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        poster.save(output_path, format="PNG")
        outputs.append(output_path)

    return outputs
