import json
from pathlib import Path

from atomize_mvp.schemas import DraftsSchema


def _normalize_cards(drafts: DraftsSchema) -> list[dict]:
    cards: list[dict] = []

    for post in drafts.linkedin_posts:
        cards.append(
            {
                "platform": "LinkedIn",
                "id": post.id,
                "title": post.hook,
                "content": post.body,
                "cta": post.cta,
                "hashtags": post.hashtags,
            }
        )

    for thread in drafts.x_threads:
        cards.append(
            {
                "platform": "X / Twitter",
                "id": thread.id,
                "title": thread.tweets[0] if thread.tweets else "",
                "content": "\n".join(thread.tweets),
                "cta": thread.closing_cta,
                "hashtags": [],
            }
        )

    for blog in drafts.blog_outlines:
        cards.append(
            {
                "platform": "Blog",
                "id": blog.id,
                "title": blog.title,
                "content": "\n".join(blog.outline),
                "cta": "",
                "hashtags": [],
            }
        )

    for story in drafts.ig_stories:
        cards.append(
            {
                "platform": "Instagram Stories",
                "id": story.id,
                "title": story.slides[0] if story.slides else "",
                "content": "\n".join(story.slides),
                "cta": "",
                "hashtags": [],
            }
        )

    return cards


def _write_cards_json(path: Path, cards: list[dict]) -> None:
    path.write_text(json.dumps(cards, indent=2, sort_keys=True), encoding="utf-8")


def _write_css(path: Path) -> None:
    css = """
:root {
  --bg: #f4f3ee;
  --card: #ffffff;
  --ink: #1f1f1f;
  --muted: #5a5a5a;
  --accent-linkedin: #0a66c2;
  --accent-x: #111111;
  --accent-blog: #d97706;
  --accent-ig: #e11d48;
  --shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", "Arial", sans-serif;
  background: radial-gradient(circle at top, #ffffff 0%, var(--bg) 60%);
  color: var(--ink);
}

header {
  padding: 32px 28px 18px 28px;
}

header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
}

header p {
  margin: 0;
  color: var(--muted);
}

section {
  padding: 12px 28px 28px 28px;
}

section h2 {
  margin: 0 0 12px 0;
  font-size: 22px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.card {
  background: var(--card);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--shadow);
  border: 2px solid transparent;
}

.badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 6px 10px;
  border-radius: 999px;
  margin-bottom: 10px;
  color: #ffffff;
}

.badge.linkedin { background: var(--accent-linkedin); }
.badge.x { background: var(--accent-x); }
.badge.blog { background: var(--accent-blog); }
.badge.ig { background: var(--accent-ig); }

.card h3 {
  margin: 6px 0 10px 0;
  font-size: 18px;
}

.card pre {
  margin: 0 0 10px 0;
  white-space: pre-wrap;
  font-family: inherit;
  color: var(--muted);
}

.meta {
  font-size: 12px;
  color: var(--muted);
}

.cta {
  margin-top: 10px;
  font-weight: 600;
}

.hashtags {
  margin-top: 8px;
  color: var(--muted);
}
"""
    path.write_text(css.strip() + "\n", encoding="utf-8")


def _render_card_html(card: dict) -> str:
    platform = card["platform"]
    badge_class = "linkedin"
    if platform.startswith("X"):
        badge_class = "x"
    elif platform.startswith("Blog"):
        badge_class = "blog"
    elif platform.startswith("Instagram"):
        badge_class = "ig"

    hashtags = " ".join(card.get("hashtags", []))
    cta = card.get("cta") or ""
    parts = [
        f'<div class="card" data-card-id="{card["id"]}">',
        f'<span class="badge {badge_class}">{platform}</span>',
        f'<div class="meta">{card["id"]}</div>',
        f'<h3>{card["title"]}</h3>',
        f'<pre>{card["content"]}</pre>',
    ]
    if cta:
        parts.append(f'<div class="cta">CTA: {cta}</div>')
    if hashtags:
        parts.append(f'<div class="hashtags">{hashtags}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _render_section(title: str, cards: list[dict]) -> str:
    card_html = "\n".join([_render_card_html(card) for card in cards])
    return f"""
<section>
  <h2>{title}</h2>
  <div class="grid">
    {card_html}
  </div>
</section>
""".strip()


def render_cards(
    job_root: Path,
    drafts: DraftsSchema,
    client: str,
    title: str,
) -> list[Path]:
    cards_dir = job_root / "04_delivery" / "Cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    cards_json = cards_dir / "cards.json"
    cards_css = cards_dir / "cards.css"
    index_html = cards_dir / "index.html"

    cards = _normalize_cards(drafts)
    _write_cards_json(cards_json, cards)
    _write_css(cards_css)

    linkedin = [c for c in cards if c["platform"] == "LinkedIn"]
    x_threads = [c for c in cards if c["platform"].startswith("X")]
    blogs = [c for c in cards if c["platform"] == "Blog"]
    ig = [c for c in cards if c["platform"].startswith("Instagram")]

    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Atomize Cards - {client} - {title}</title>
    <link rel="stylesheet" href="cards.css" />
  </head>
  <body>
    <header>
      <h1>Atomize Cards</h1>
      <p>{client} — {title}</p>
    </header>
    {_render_section("LinkedIn", linkedin)}
    {_render_section("X / Twitter", x_threads)}
    {_render_section("Blogs", blogs)}
    {_render_section("Instagram Stories", ig)}
  </body>
</html>
"""
    index_html.write_text(html.strip() + "\n", encoding="utf-8")

    return [index_html, cards_css, cards_json]
