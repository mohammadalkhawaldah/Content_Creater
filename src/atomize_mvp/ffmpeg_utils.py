import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_ffmpeg() -> None:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("ffmpeg found: %s", result.stdout.splitlines()[0])
    except FileNotFoundError as exc:
        msg = (
            "ffmpeg is not available. Install ffmpeg and ensure it is on PATH. "
            "On Windows, you can install with: winget install Gyan.FFmpeg"
        )
        logger.error(msg)
        raise RuntimeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = "ffmpeg is installed but returned an error when checking version."
        logger.error(msg)
        raise RuntimeError(msg) from exc


def convert_to_mp4(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(output_path),
    ]
    logger.info("Converting to mp4 with ffmpeg")
    subprocess.run(cmd, check=True)


def split_audio(input_path: Path, output_dir: Path, segment_seconds: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "chunk_%03d.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-f",
        "segment",
        "-segment_time",
        str(segment_seconds),
        "-reset_timestamps",
        "1",
        "-c",
        "copy",
        str(pattern),
    ]
    logger.info("Splitting audio into %ss chunks", segment_seconds)
    subprocess.run(cmd, check=True)
    return sorted(output_dir.glob("chunk_*.mp4"))
