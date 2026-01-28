import base64
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from atomize_mvp.llm_client import generate_image_base64
from atomize_mvp.schemas import VisualBlueprint, VisualSection

PLATFORM_FOLDERS = {
    "LinkedIn": "LinkedIn",
    "X / Twitter": "X",
    "Instagram Stories": "Instagram",
    "Blog": "Blogs",
}

ICON_MAP = {
    "drone": "🚁",
    "ai": "🤖",
    "map": "🗺️",
    "data": "📊",
    "network": "🧠",
}

BASE_STYLE = (
    "minimal, abstract, clean, modern, tech and AI theme, blue and teal palette, "
    "soft gradients, no text"
)


def structured_output_path(root: Path, platform: str, content_id: str) -> Path:
    folder = PLATFORM_FOLDERS.get(platform, "Other")
    return root / folder / f"{content_id}.png"


def _pick_icon_keyword(text: str) -> str:
    lowered = text.lower()
    if "drone" in lowered:
        return "drone"
    if "network" in lowered or "connect" in lowered:
        return "network"
    if "map" in lowered or "route" in lowered:
        return "map"
    if "data" in lowered or "insight" in lowered:
        return "data"
    return "ai"


def _extract_points(content: str, max_points: int = 4) -> list[str]:
    lines = [line.strip("•- ").strip() for line in content.splitlines() if line.strip()]
    if len(lines) >= max_points:
        return lines[:max_points]
    sentences = re.split(r"[.!?]\s+", content.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        return sentences[:max_points]
    return [content.strip()][:max_points]


def generate_visual_blueprints(cards_dir: Path, output_dir: Path, count: int) -> list[Path]:
    cards_json = cards_dir / "cards.json"
    cards = json.loads(cards_json.read_text(encoding="utf-8"))
    heroes = [card for card in cards if card.get("hero") is True]
    selected = heroes[:count] if heroes else cards[:count]

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for card in selected:
        title = card.get("title", "").strip()
        content = card.get("content", "").strip()
        subtitle = ""
        points = _extract_points(content, max_points=4)
        sections = []
        for point in points[:4]:
            keyword = _pick_icon_keyword(point or title)
            sections.append(VisualSection(icon=keyword, text=point))
        if len(sections) < 3:
            while len(sections) < 3:
                sections.append(VisualSection(icon="ai", text=title or "Key insight"))

        blueprint = VisualBlueprint(
            title=title or card["id"],
            subtitle=subtitle,
            sections=sections[:4],
            visual_hint=f"{title or 'technology'} illustration, {BASE_STYLE}",
        )
        output_path = output_dir / f"{card['id']}.json"
        output_path.write_text(
            json.dumps(blueprint.model_dump(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        outputs.append(output_path)

    return outputs


def _render_template(blueprint: VisualBlueprint, image_data_uri: str, template: str) -> str:
    icon_html = "\n".join(
        [
            f"<li><span class='icon'>{ICON_MAP.get(s.icon, '✨')}</span>{s.text}</li>"
            for s in blueprint.sections
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      body {{ margin: 0; background: #0f172a; }}
      .poster {{
        width: 1080px; height: 1080px; background: #0b1220;
        color: #f8fafc; font-family: "Segoe UI", Arial, sans-serif;
        display: flex; flex-direction: column; padding: 64px;
        box-sizing: border-box;
        background-image: radial-gradient(circle at top, #1e3a8a 0%, #0b1220 60%);
      }}
      .title {{ font-size: 56px; font-weight: 700; margin: 0 0 12px 0; }}
      .subtitle {{ font-size: 24px; color: #cbd5f5; margin-bottom: 24px; }}
      .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 28px; flex: 1; }}
      .panel {{ background: rgba(255,255,255,0.04); border-radius: 24px; padding: 24px; }}
      .visual {{ display: flex; align-items: center; justify-content: center; }}
      .visual img {{ width: 100%; max-width: 360px; border-radius: 18px; }}
      ul {{ list-style: none; padding: 0; margin: 0; }}
      li {{ margin-bottom: 16px; font-size: 22px; }}
      .icon {{ margin-right: 12px; }}
    </style>
  </head>
  <body>
    <div class="poster" id="poster">
      <div class="title">{blueprint.title}</div>
      <div class="subtitle">{blueprint.subtitle}</div>
      {template}
    </div>
  </body>
</html>""".replace("{{IMAGE}}", image_data_uri).replace("{{ITEMS}}", icon_html)


def _template_a() -> str:
    return """
      <div class="grid">
        <div class="panel visual">
          <img src="{{IMAGE}}" alt="visual" />
        </div>
        <div class="panel">
          <ul>{{ITEMS}}</ul>
        </div>
      </div>
    """


def _template_b() -> str:
    return """
      <div class="grid">
        <div class="panel">
          <ul>{{ITEMS}}</ul>
        </div>
        <div class="panel visual">
          <img src="{{IMAGE}}" alt="visual" />
        </div>
      </div>
    """


def export_structured_posters(
    cards_dir: Path,
    blueprints: list[Path],
    posters_root: Path,
    model: str,
) -> list[Path]:
    cards_json = cards_dir / "cards.json"
    cards = {card["id"]: card for card in json.loads(cards_json.read_text(encoding="utf-8"))}
    outputs: list[Path] = []

    posters_root.mkdir(parents=True, exist_ok=True)
    template_a = _template_a()
    template_b = _template_b()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080, "deviceScaleFactor": 1})
        for idx, blueprint_path in enumerate(blueprints):
            blueprint = VisualBlueprint.model_validate(
                json.loads(blueprint_path.read_text(encoding="utf-8"))
            )
            card = cards.get(blueprint_path.stem)
            if not card:
                continue
            prompt = blueprint.visual_hint
            image_b64 = generate_image_base64(prompt, model=model, size="1024x1024")
            image_data_uri = f"data:image/png;base64,{image_b64}"
            template = template_a if idx % 2 == 0 else template_b
            html = _render_template(blueprint, image_data_uri, template)
            page.set_content(html, wait_until="load")
            element = page.query_selector("#poster")
            output_path = structured_output_path(posters_root, card["platform"], card["id"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            element.screenshot(path=str(output_path))
            outputs.append(output_path)
        browser.close()

    return outputs
