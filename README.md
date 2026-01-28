# Atomize MVP

Atomize is a CLI tool that turns long-form audio/video into a client-ready content library package.

## Phase 1 scope
- Repo structure and CLI scaffolding
- Logging and delivery folder creation
- Resume capability for completed steps (skip unless `--force`)

## Setup
1) Create and activate a Python 3.11+ environment
2) Install dependencies and the package:

```bash
pip install -r requirements.txt
pip install -e .
```

## CLI

```bash
python -m atomize_mvp run --input <path> --client <name> --title <title> --out <folder>
```

## Delivery folder structure (Phase 1)

```
<out>/<client>/<title>/
  01_source/
  02_transcripts/
    audio.mp4 (for audio/video inputs)
  03_content/
  04_delivery/
  logs/
  .atomize/
```

## Phase 1 test

```bash
python -m atomize_mvp run --input .\tests\data\sample.txt --client "Acme" --title "Kickoff" --out .\out
```

Expected:
- Creates delivery folder tree under `.\out\acme\kickoff\`
- Writes `.\out\acme\kickoff\.atomize\steps.json`
- Writes log file at `.\out\acme\kickoff\logs\atomize.log`
