import json
import os
import subprocess
import sys
from pathlib import Path

from atomize_mvp.schemas import ContentBlueprint


def test_blueprint_offline(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_path = repo_root / "tests" / "data" / "sample.txt"
    out_root = tmp_path / "out"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["ATOMIZE_OFFLINE"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "atomize_mvp",
        "run",
        "--input",
        str(input_path),
        "--client",
        "Acme",
        "--title",
        "Kickoff",
        "--out",
        str(out_root),
    ]
    subprocess.run(cmd, check=True, env=env)

    job_root = out_root / "acme" / "kickoff"
    blueprint_path = job_root / "03_content" / "blueprint" / "content_blueprint.json"
    assert blueprint_path.exists()

    data = json.loads(blueprint_path.read_text(encoding="utf-8"))
    ContentBlueprint.model_validate(data)

    steps = json.loads((job_root / ".atomize" / "steps.json").read_text(encoding="utf-8"))
    assert steps["steps"]["blueprint"]["status"] == "done"
