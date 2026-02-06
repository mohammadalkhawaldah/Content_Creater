from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _rel_url(path: Path, out_root: Path) -> str:
    rel = path.relative_to(out_root)
    return f"/out/{rel.as_posix()}"


def _started_at(job_root: Path) -> datetime | None:
    marker = job_root / ".atomize" / "web_job.json"
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        value = data.get("started_at")
    except json.JSONDecodeError:
        return None
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _include_path(path: Path, started_at: datetime | None) -> bool:
    if started_at is None:
        return True
    # Allow small clock/FS timestamp skew so freshly written files are included.
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime >= (started_at - timedelta(seconds=5))


def build_results(out_root: Path, job_root: Path) -> dict:
    delivery = job_root / "04_delivery"
    drafts_path = job_root / "03_content" / "drafts" / "drafts.json"
    quick_path = job_root / "03_content" / "quick" / "quick_bundle.json"
    manifest_path = delivery / "run_manifest.json"
    started_at = _started_at(job_root)

    results = {
        "summary": None,
        "drafts": {},
        "posters": {},
        "docs": [],
        "cards": [],
        "manifest": None,
    }

    if drafts_path.exists() and _include_path(drafts_path, started_at):
        data = json.loads(drafts_path.read_text(encoding="utf-8"))
        results["drafts"] = {
            "linkedin": data.get("linkedin_posts", []),
            "x": data.get("x_threads", []),
            "blog": data.get("blog_outlines", []),
            "ig": data.get("ig_stories", []),
        }
        if quick_path.exists() and _include_path(quick_path, started_at):
            try:
                quick_data = json.loads(quick_path.read_text(encoding="utf-8"))
                results["summary"] = quick_data.get("summary")
            except json.JSONDecodeError:
                pass
    elif quick_path.exists() and _include_path(quick_path, started_at):
        data = json.loads(quick_path.read_text(encoding="utf-8"))
        results["summary"] = data.get("summary")
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
            images = [p for p in folder.rglob("*.png") if _include_path(p, started_at)]
            if images:
                posters[folder.name] = [
                    {"name": p.name, "path": str(p), "url": _rel_url(p, out_root)}
                    for p in images
                ]
        results["posters"] = posters

        cards_dir = delivery / "Cards"
        if cards_dir.exists():
            for path in cards_dir.rglob("*.html"):
                if not _include_path(path, started_at):
                    continue
                results["cards"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )
            for path in cards_dir.rglob("*.json"):
                if not _include_path(path, started_at):
                    continue
                results["cards"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )

        for ext in ("*.docx", "*.csv"):
            for path in delivery.rglob(ext):
                if not _include_path(path, started_at):
                    continue
                results["docs"].append(
                    {"name": path.name, "path": str(path), "url": _rel_url(path, out_root)}
                )

    if manifest_path.exists() and _include_path(manifest_path, started_at):
        results["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))

    return results
