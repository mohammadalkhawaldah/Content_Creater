from datetime import date
from pathlib import Path

from atomize_mvp.finalize import finalize_delivery
from atomize_mvp.schemas import ContentBlueprint, DraftsSchema, LinkedinPost, XThread, BlogOutline, IGStory


def test_finalize_delivery_outputs(tmp_path: Path) -> None:
    job_root = tmp_path / "job"
    (job_root / "02_transcripts").mkdir(parents=True, exist_ok=True)
    (job_root / "04_delivery" / "Platform Ready").mkdir(parents=True, exist_ok=True)

    # Seed minimal transcript files for copying
    (job_root / "02_transcripts" / "transcript.txt").write_text("t", encoding="utf-8")
    (job_root / "02_transcripts" / "clean_transcript.txt").write_text("t", encoding="utf-8")
    (job_root / "02_transcripts" / "transcript.srt").write_text("t", encoding="utf-8")
    (job_root / "02_transcripts" / "segments.json").write_text("[]", encoding="utf-8")

    drafts = DraftsSchema(
        linkedin_posts=[
            LinkedinPost(
                id="LI-01",
                hook="Hook",
                body="Body",
                cta="CTA",
                hashtags=["#tag"],
            )
        ],
        x_threads=[
            XThread(
                id="X-01",
                tweets=["T1", "T2", "T3"],
                closing_cta="CTA",
            )
        ],
        blog_outlines=[
            BlogOutline(
                id="B-01",
                title="Title",
                audience="Audience",
                goal="Goal",
                outline=["O1", "O2", "O3"],
                key_takeaways=["K1", "K2", "K3"],
            )
        ],
        ig_stories=[
            IGStory(
                id="IG-01",
                slides=["S1", "S2", "S3"],
            )
        ],
    )

    blueprint = ContentBlueprint(
        title="Title",
        summary="Summary",
        key_points=["P1"] * 8,
        hooks=["H1"] * 10,
        quotes=["Q1"] * 10,
        ctas=["C1"] * 8,
        do_not_say=["D1"] * 5,
    )

    outputs = finalize_delivery(
        job_root=job_root,
        drafts=drafts,
        blueprint=blueprint,
        client="Acme",
        title="Kickoff",
        lang="en",
        tone="professional friendly",
        include_schedule=True,
        base_date=date(2026, 1, 1),
    )

    assert outputs.content_library.exists()
    assert outputs.hooks_quotes.exists()
    assert outputs.readme.exists()
    assert outputs.schedule is not None
    assert outputs.schedule.exists()
