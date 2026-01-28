from pathlib import Path

from atomize_mvp.ai_posters import ai_poster_output_path, build_background_prompt, select_hero_cards


def test_ai_poster_output_path():
    root = Path("posters_ai")
    assert ai_poster_output_path(root, "LinkedIn", "LI-01").as_posix().endswith(
        "posters_ai/LinkedIn/LI-01.png"
    )


def test_background_prompt_contains_style():
    card = {"id": "LI-01", "platform": "LinkedIn", "title": "AI drones in logistics"}
    prompt = build_background_prompt(card)
    assert "no text" in prompt.lower()
    assert "blue" in prompt.lower()


def test_select_hero_cards():
    cards = [
        {"id": "LI-01", "hero": True},
        {"id": "X-01"},
    ]
    selected = select_hero_cards(cards, 5)
    assert selected == [{"id": "LI-01", "hero": True}]
