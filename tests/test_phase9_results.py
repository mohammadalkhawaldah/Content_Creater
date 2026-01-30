from pathlib import Path

from atomize_mvp.web_results import build_results


def test_build_results(tmp_path: Path) -> None:
    out_root = tmp_path / "out"
    job_root = out_root / "acme" / "kickoff"
    (job_root / "03_content" / "drafts").mkdir(parents=True, exist_ok=True)
    (job_root / "04_delivery" / "Posters" / "LinkedIn").mkdir(parents=True, exist_ok=True)
    (job_root / "04_delivery" / "Cards").mkdir(parents=True, exist_ok=True)

    (job_root / "03_content" / "drafts" / "drafts.json").write_text(
        '{"linkedin_posts":[{"id":"LI-01","hook":"h","body":"b"}]}',
        encoding="utf-8",
    )
    (job_root / "04_delivery" / "Posters" / "LinkedIn" / "LI-01.png").write_bytes(b"img")
    (job_root / "04_delivery" / "Cards" / "index.html").write_text("<html></html>", encoding="utf-8")
    (job_root / "04_delivery" / "README - Start Here - Acme - Kickoff.docx").write_bytes(b"doc")

    results = build_results(out_root, job_root)
    assert results["drafts"]["linkedin"][0]["id"] == "LI-01"
    assert "Posters" in results["posters"]
    assert results["docs"]
