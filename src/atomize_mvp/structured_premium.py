import base64
import json
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

from atomize_mvp.design_system import Theme, get_theme
from atomize_mvp.llm_client import generate_image_base64
from atomize_mvp.schemas import VisualBlueprint

PLATFORM_FOLDERS = {
    "LinkedIn": "LinkedIn",
    "X / Twitter": "X",
    "Instagram Stories": "Instagram",
    "Blog": "Blogs",
}

ICON_NAMES = {"drone", "ai", "map", "data", "network"}


def premium_output_path(root: Path, platform: str, content_id: str) -> Path:
    folder = PLATFORM_FOLDERS.get(platform, "Other")
    return root / folder / f"{content_id}.png"


def _load_icon_svg(name: str) -> str:
    icon_path = Path(__file__).parent / "assets" / "icons" / f"{name}.svg"
    return icon_path.read_text(encoding="utf-8")


def _icon_data_uri(name: str) -> str:
    svg = _load_icon_svg(name)
    svg = svg.replace('fill="currentColor"', 'fill="currentColor"')
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml;utf8,{encoded}"


def _build_html(
    blueprint: VisualBlueprint,
    platform: str,
    theme: Theme,
    image_data_uri: str | None,
    font_path: str | None,
) -> str:
    icon_html = "\n".join(
        [
            f"""
            <div class="feature-card">
              <div class="icon-wrap">
                <img src="{_icon_data_uri(section.icon if section.icon in ICON_NAMES else 'ai')}" alt="{section.icon}" />
              </div>
              <div class="feature-text">{section.text}</div>
            </div>
            """
            for section in blueprint.sections
        ]
    )

    font_face = ""
    if font_path:
        font_url = Path(font_path).resolve().as_uri()
        font_face = (
            "@font-face { font-family: 'AtomizeCustom'; src: "
            f"url('{font_url}'); font-weight: 400; }}"
        )

    title = blueprint.title
    subtitle = blueprint.subtitle
    font_family = "AtomizeCustom" if font_path else "Segoe UI"

    anchor_html = ""
    if image_data_uri:
        anchor_html = f"""
        <div class="anchor">
          <img src="{image_data_uri}" alt="visual anchor" />
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      {font_face}
      body {{
        margin: 0;
        background: {theme.background};
      }}
      .poster {{
        width: 1080px;
        height: 1080px;
        box-sizing: border-box;
        font-family: {font_family}, Arial, sans-serif;
        color: {theme.text_body};
        padding: {theme.margin}px;
        background: {theme.background};
        position: relative;
        overflow: hidden;
      }}
      .header {{
        height: 24%;
        border-radius: {theme.card_radius}px;
        background: linear-gradient(135deg, {theme.gradients[0]}, {theme.gradients[1]}, {theme.gradients[2]});
        padding: {theme.padding}px;
        color: {theme.badge_text};
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: {theme.padding}px;
        box-shadow: {theme.shadow};
      }}
      .badge {{
        display: inline-block;
        background: rgba(255, 255, 255, 0.2);
        color: {theme.badge_text};
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
      }}
      .title {{
        font-size: {theme.title_size}px;
        font-weight: {theme.title_weight};
        color: {theme.badge_text};
        margin: 0;
        line-height: 1.1;
      }}
      .subtitle {{
        font-size: {theme.subtitle_size}px;
        color: rgba(255, 255, 255, 0.85);
        margin-top: 8px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: {theme.padding}px;
      }}
      .feature-card {{
        background: #ffffff;
        border-radius: {theme.card_radius}px;
        padding: 24px;
        box-shadow: {theme.shadow};
        display: flex;
        flex-direction: column;
        gap: 16px;
      }}
      .icon-wrap {{
        width: 54px;
        height: 54px;
        border-radius: 16px;
        background: rgba(14, 165, 233, 0.12);
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .icon-wrap img {{
        width: 32px;
        height: 32px;
        filter: brightness(0) saturate(100%) invert(24%) sepia(98%) saturate(2458%)
          hue-rotate(188deg) brightness(96%) contrast(101%);
      }}
      .feature-text {{
        font-size: {theme.bullet_size}px;
        line-height: {theme.line_height};
        color: {theme.text_body};
      }}
      .anchor {{
        position: absolute;
        right: {theme.margin}px;
        bottom: {theme.margin}px;
        width: 200px;
        height: 200px;
        border-radius: 50%;
        overflow: hidden;
        box-shadow: {theme.shadow};
        border: 6px solid #ffffff;
        background: #ffffff;
      }}
      .anchor img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
      }}
    </style>
  </head>
  <body>
    <div class="poster" id="poster">
      <div class="header">
        <div class="badge">{platform}</div>
        <h1 class="title">{title}</h1>
        <div class="subtitle">{subtitle}</div>
      </div>
      <div class="grid">
        {icon_html}
      </div>
      {anchor_html}
    </div>
  </body>
</html>
"""


def export_structured_posters_premium(
    cards_dir: Path,
    blueprints_dir: Path,
    posters_root: Path,
    theme_name: str,
    model: str,
    font_path: str | None,
) -> list[Path]:
    cards = json.loads((cards_dir / "cards.json").read_text(encoding="utf-8"))
    cards_by_id = {card["id"]: card for card in cards}
    theme = get_theme(theme_name)

    posters_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080, "deviceScaleFactor": 1})
        for blueprint_path in sorted(blueprints_dir.glob("*.json")):
            blueprint = VisualBlueprint.model_validate_json(
                blueprint_path.read_text(encoding="utf-8")
            )
            card = cards_by_id.get(blueprint_path.stem)
            if not card:
                continue
            visual_prompt = blueprint.visual_hint
            image_b64 = generate_image_base64(visual_prompt, model=model, size="1024x1024")
            image_data_uri = f"data:image/png;base64,{image_b64}"
            html = _build_html(
                blueprint=blueprint,
                platform=card["platform"],
                theme=theme,
                image_data_uri=image_data_uri,
                font_path=font_path,
            )
            page.set_content(html, wait_until="load")
            element = page.query_selector("#poster")
            output_path = premium_output_path(posters_root, card["platform"], card["id"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            element.screenshot(path=str(output_path))
            outputs.append(output_path)
        browser.close()

    return outputs
