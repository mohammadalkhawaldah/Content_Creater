from pathlib import Path

from atomize_mvp.paths import build_delivery_root, slugify


def test_slugify_basic():
    assert slugify("Acme Inc") == "acme_inc"
    assert slugify("  ") == "untitled"


def test_build_delivery_root():
    root = build_delivery_root(Path("out"), "Acme Inc", "Kickoff Call")
    assert root.as_posix().endswith("out/acme_inc/kickoff_call")
