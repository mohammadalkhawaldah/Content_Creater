import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PLATFORM_FOLDERS = {
    "LinkedIn": "LinkedIn",
    "X / Twitter": "X",
    "Instagram Stories": "Instagram",
    "Blog": "Blogs",
}


def poster_output_path(posters_root: Path, platform: str, content_id: str) -> Path:
    folder = PLATFORM_FOLDERS.get(platform, "Other")
    return posters_root / folder / f"{content_id}.png"


def export_posters(cards_dir: Path, posters_root: Path) -> list[Path]:
    cards_json = cards_dir / "cards.json"
    index_html = cards_dir / "index.html"
    if not cards_json.exists() or not index_html.exists():
        raise FileNotFoundError("Cards output missing. Run render_cards first.")

    cards = json.loads(cards_json.read_text(encoding="utf-8"))
    posters_root.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1200, "deviceScaleFactor": 2})
        page.goto(index_html.resolve().as_uri())

        for card in cards:
            content_id = card["id"]
            platform = card["platform"]
            element = page.wait_for_selector(
                f'[data-card-id="{content_id}"]', timeout=5000
            )
            element.scroll_into_view_if_needed()
            output_path = poster_output_path(posters_root, platform, content_id)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            element.screenshot(path=str(output_path))
            outputs.append(output_path)

        browser.close()

    return outputs
