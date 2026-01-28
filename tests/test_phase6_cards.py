from pathlib import Path

from atomize_mvp.cards import render_cards
from atomize_mvp.schemas import BlogOutline, DraftsSchema, IGStory, LinkedinPost, XThread


def test_render_cards_outputs(tmp_path: Path) -> None:
    job_root = tmp_path / "job"
    job_root.mkdir(parents=True, exist_ok=True)

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
                tweets=["Tweet 1", "Tweet 2", "Tweet 3"],
                closing_cta="CTA",
            )
        ],
        blog_outlines=[
            BlogOutline(
                id="B-01",
                title="Title",
                audience="Audience",
                goal="Goal",
                outline=["Point 1", "Point 2", "Point 3"],
                key_takeaways=["Takeaway 1", "Takeaway 2", "Takeaway 3"],
            )
        ],
        ig_stories=[
            IGStory(
                id="IG-01",
                slides=["Slide 1", "Slide 2", "Slide 3"],
            )
        ],
    )

    outputs = render_cards(job_root, drafts, client="Acme", title="Kickoff")
    for path in outputs:
        assert path.exists()
        assert path.stat().st_size > 0
