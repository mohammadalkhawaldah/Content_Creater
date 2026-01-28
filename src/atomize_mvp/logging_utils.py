import logging
from pathlib import Path

from atomize_mvp.paths import build_delivery_root, delivery_tree


def configure_logging(out_root: Path, client: str, title: str, level: str) -> None:
    root = build_delivery_root(out_root, client, title)
    tree = delivery_tree(root)
    tree["logs"].mkdir(parents=True, exist_ok=True)
    log_path = tree["logs"] / "atomize.log"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
