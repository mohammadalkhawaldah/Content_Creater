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

## Web App (Phase 9)

Start the local web server:

```bash
python -m atomize_mvp web --host 127.0.0.1 --port 8000 --out ./out
```

Open your browser at:
```
http://127.0.0.1:8000
```

The UI lets you upload audio/video/text, configure counts/tone/language, run a job, view results, and download a ZIP.

### Results Location
All outputs are stored under:
```
out/<client>/<title>/04_delivery/
```

### Troubleshooting (Windows)
- If DOCX files are locked, close them and re-run.
- If file paths are too long, move the repo closer to the drive root (e.g., `C:\Atomize`).

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
