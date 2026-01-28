from atomize_mvp.design_system import get_theme
from atomize_mvp.structured_premium import premium_output_path
from pathlib import Path


def test_theme_bright_canva():
    theme = get_theme("bright_canva")
    assert theme.background == "#FFFFFF"


def test_premium_output_path():
    root = Path("premium")
    assert premium_output_path(root, "LinkedIn", "LI-01").as_posix().endswith(
        "premium/LinkedIn/LI-01.png"
    )
