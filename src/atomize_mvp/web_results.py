from __future__ import annotations

import json
from pathlib import Path


def _rel_url(path: Path, out_root: Path) -> str:
    rel = path.relative_to(out_root)
    return f"/out/{rel.as_posix()}"


def build_results(out_root: Path, job_root: Path) -> dict:
    delivery = job_root / "04_delivery"
    drafts_path = job_root / "03_content" / "drafts" / "drafts.json"
    manifest_path = delivery / "run_manifest.json"

    results = {
        "drafts": {},
        "posters": {},
        "docs": [],
        "cards": [],
        "manifest": None,
    }

    if drafts_path.exists():
        data = json.loads(drafts_path.read_text(encoding="utf-8"))
        results["drafts"] = {
            "linkedin": data.get("linkedin_posts", []),
            "x": data.get("x_threads", []),
            "blog": data.get("blog_outlines", []),
            "ig": data.get("ig_stories", []),
        }

    if delivery.exists():
        posters = {}
        for folder in delivery.glob("Posters*"):
            if not folder.is_dir():
                continue
            images = [p for p in folder.rglob("*.png")]
            if images:
                posters[folder.name] = [
                    {"name": p.name, "path": str(p), "url": _rel_url(p, out_root)}
                    for p in images
                ]
        results["posters"] = posters

        cards_dir = delivery / "Cards"
        if cards_dir.exists():
            for path in cards_dir.rglob("*.html"):
                results["cards"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )
            for path in cards_dir.rglob("*.json"):
                results["cards"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )

        for ext in ("*.docx", "*.csv"):
            for path in delivery.rglob(ext):
                results["docs"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )

    if manifest_path.exists():
        results["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))

    return results
