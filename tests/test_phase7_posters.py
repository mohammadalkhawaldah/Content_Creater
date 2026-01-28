from pathlib import Path

from atomize_mvp.render_posters import poster_output_path


def test_poster_output_path():
    root = Path("posters")
    assert poster_output_path(root, "LinkedIn", "LI-01").as_posix().endswith(
        "posters/LinkedIn/LI-01.png"
    )
    assert poster_output_path(root, "X / Twitter", "X-01").as_posix().endswith(
        "posters/X/X-01.png"
    )
    assert poster_output_path(root, "Instagram Stories", "IG-01").as_posix().endswith(
        "posters/Instagram/IG-01.png"
    )
    assert poster_output_path(root, "Blog", "B-01").as_posix().endswith(
        "posters/Blogs/B-01.png"
    )
