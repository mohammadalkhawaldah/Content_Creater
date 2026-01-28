from pathlib import Path

from atomize_mvp.delivery import (
    write_blog_outlines_docx,
    write_ig_stories_docx,
    write_linkedin_docx,
    write_x_threads_docx,
)
from atomize_mvp.drafts import write_drafts_json
from atomize_mvp.schemas import BlogOutline, DraftsSchema, IGStory, LinkedinPost, XThread


def test_phase4_write_outputs(tmp_path: Path) -> None:
    drafts = DraftsSchema(
        linkedin_posts=[
            LinkedinPost(
                id="LI-01",
                hook="Hook",
                body="Body",
                cta="CTA",
                hashtags=["#test"],
            )
        ],
        x_threads=[
            XThread(
                id="X-01",
                tweets=["Tweet 1", "Tweet 2", "Tweet 3"],
                closing_cta="Closing",
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

    drafts_json = tmp_path / "drafts.json"
    write_drafts_json(drafts_json, drafts)
    assert drafts_json.exists()

    delivery_dir = tmp_path / "delivery"
    write_linkedin_docx(delivery_dir / "LinkedIn_Posts.docx", drafts)
    write_x_threads_docx(delivery_dir / "X_Threads.docx", drafts)
    write_blog_outlines_docx(delivery_dir / "Blog_Outlines.docx", drafts)
    write_ig_stories_docx(delivery_dir / "IG_Stories.docx", drafts)

    assert (delivery_dir / "LinkedIn_Posts.docx").exists()
    assert (delivery_dir / "X_Threads.docx").exists()
    assert (delivery_dir / "Blog_Outlines.docx").exists()
    assert (delivery_dir / "IG_Stories.docx").exists()
