import json
import os
import subprocess
import sys
from pathlib import Path


def test_txt_input_transcription_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_path = repo_root / "tests" / "data" / "sample.txt"
    out_root = tmp_path / "out"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

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
    transcripts_dir = job_root / "02_transcripts"

    transcript = transcripts_dir / "transcript.txt"
    clean_transcript = transcripts_dir / "clean_transcript.txt"
    segments = transcripts_dir / "segments.json"
    srt = transcripts_dir / "transcript.srt"

    assert transcript.exists()
    assert clean_transcript.exists()
    assert segments.exists()
    assert srt.exists()

    segments_data = json.loads(segments.read_text(encoding="utf-8"))
    assert isinstance(segments_data, list)
    assert len(segments_data) == 1

    steps = json.loads((job_root / ".atomize" / "steps.json").read_text(encoding="utf-8"))
    assert steps["steps"]["transcribe"]["status"] == "done"
    assert steps["steps"]["cleanup_transcript"]["status"] == "done"
