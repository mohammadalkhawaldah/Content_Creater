import re
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "untitled"


def build_delivery_root(out_root: Path, client: str, title: str) -> Path:
    return out_root / slugify(client) / slugify(title)


def delivery_tree(root: Path) -> dict:
    return {
        "root": root,
        "source": root / "01_source",
        "transcripts": root / "02_transcripts",
        "content": root / "03_content",
        "delivery": root / "04_delivery",
        "logs": root / "logs",
        "state": root / ".atomize",
    }
