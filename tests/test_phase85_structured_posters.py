from pathlib import Path

from atomize_mvp.structured_posters import generate_visual_blueprints, structured_output_path
from atomize_mvp.schemas import VisualBlueprint


def test_structured_output_path():
    root = Path("structured")
    assert structured_output_path(root, "LinkedIn", "LI-01").as_posix().endswith(
        "structured/LinkedIn/LI-01.png"
    )


def test_visual_blueprints(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "cards.json").write_text(
        '[{"id":"LI-01","platform":"LinkedIn","title":"AI drones","content":"Point one. Point two."}]',
        encoding="utf-8",
    )
    out_dir = tmp_path / "blueprints"
    outputs = generate_visual_blueprints(cards_dir, out_dir, 1)
    assert outputs
    data = outputs[0].read_text(encoding="utf-8")
    VisualBlueprint.model_validate_json(data)
