from pathlib import Path

from atomize_mvp.web_zip import _zip_folder


def test_zip_builder(tmp_path: Path) -> None:
    root = tmp_path / "final"
    (root / "sub").mkdir(parents=True, exist_ok=True)
    (root / "sub" / "file.txt").write_text("hello", encoding="utf-8")

    zip_path = _zip_folder(root)
    assert zip_path.exists()
