# Transcribe CLI — Project Spec

## Overview

A local-first CLI tool for batch transcribing audio/video files using `mlx-whisper` on Apple Silicon. It processes an input directory of media files, writes transcription output (as `.txt` and/or `.json`) to an output directory, and tracks progress so interrupted runs can resume.

## Stack

- **Python 3.12+**
- **uv** for project management (pyproject.toml, lockfile, virtual env)
- **mlx-whisper** for transcription (Apple Silicon optimized)
- **typer** for CLI (modern, type-hint driven)
- **rich** for terminal progress bars and status output
- **SQLite** (stdlib) for tracking job state

## Project Setup

```bash
uv init transcribe-cli
cd transcribe-cli
uv add mlx-whisper typer rich
```

Use `uv run` to execute all commands. No global installs.

## Directory Structure

```
transcribe-cli/
├── pyproject.toml
├── README.md
├── src/
│   └── transcribe_cli/
│       ├── __init__.py
│       ├── cli.py          # Typer CLI entrypoint
│       ├── transcriber.py  # Core transcription logic wrapping mlx-whisper
│       ├── tracker.py      # SQLite job tracker (progress, status, resume)
│       ├── scanner.py      # File discovery and filtering
│       └── config.py       # Default settings, model config
└── tests/
    ├── test_scanner.py
    ├── test_tracker.py
    └── test_transcriber.py
```

Register the CLI entrypoint in `pyproject.toml`:

```toml
[project.scripts]
transcribe = "transcribe_cli.cli:main"
```

## Supported File Types

Scan for these extensions (case-insensitive):

- Audio: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`
- Video: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`

## SQLite Tracker Schema

Store job state in `.transcribe-cli/jobs.db` inside the output directory.

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    input_path TEXT UNIQUE NOT NULL,
    output_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | processing | completed | failed
    error TEXT,
    duration_seconds REAL,          -- audio duration
    processing_seconds REAL,        -- how long transcription took
    model TEXT,                      -- which whisper model was used
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);
```

## CLI Commands

### `transcribe run`

Main batch processing command.

```
transcribe run <input_dir> <output_dir> [OPTIONS]

Options:
  --model TEXT          Model to use [default: mlx-community/whisper-large-v3-turbo]
  --format TEXT         Output format: txt, json, or both [default: txt]
  --language TEXT       Language code, e.g. "en" [default: auto-detect]
  --overwrite           Re-transcribe files even if already completed
  --workers INT         Number of concurrent files [default: 1]
```

Behavior:
1. Scan `input_dir` recursively for supported media files
2. For each file, compute the expected output path (mirror directory structure in `output_dir`)
3. Check tracker DB — skip files already marked `completed` (unless `--overwrite`)
4. Mark file as `processing`, run transcription, write output, mark `completed`
5. On failure, mark `failed` with error message and continue to next file
6. Display a `rich` progress bar showing: files completed / total, current file name, elapsed time

### `transcribe single`

Run a single file for quick testing and verification.

```
transcribe single <file_path> [OPTIONS]

Options:
  --model TEXT          Model to use [default: mlx-community/whisper-large-v3-turbo]
  --output TEXT         Output file path [default: stdout]
  --format TEXT         Output format: txt or json [default: txt]
  --language TEXT       Language code [default: auto-detect]
```

Behavior:
1. Transcribe the single file
2. Print result to stdout by default (or write to `--output`)
3. Print timing info to stderr (duration, processing time, RTF)
4. Does NOT interact with the tracker DB

### `transcribe status`

Show progress for a batch job.

```
transcribe status <output_dir>
```

Behavior:
1. Read the tracker DB in the output directory
2. Display a summary table:
   - Total files found
   - Completed / Pending / Failed counts
   - Total audio duration processed
   - Total processing time
   - Average real-time factor (RTF)
3. If there are failed files, list them with their error messages

### `transcribe retry`

Retry all failed files.

```
transcribe retry <output_dir> [OPTIONS]

Options:
  --model TEXT          Model to use [default: same as original run]
```

Behavior:
1. Find all files with `status = 'failed'` in the tracker DB
2. Reset them to `pending` and re-run transcription
3. Show progress bar as with `run`

### `transcribe list`

List all tracked files and their statuses.

```
transcribe list <output_dir> [OPTIONS]

Options:
  --status TEXT    Filter by status: pending, processing, completed, failed
  --sort TEXT      Sort by: name, status, duration [default: name]
```

## Output Format

### txt format
Plain text transcription, one file per input file.
```
input_dir/podcast/ep01.mp3  →  output_dir/podcast/ep01.txt
```

### json format
Structured output with segments and timestamps:
```json
{
  "file": "ep01.mp3",
  "model": "mlx-community/whisper-large-v3-turbo",
  "language": "en",
  "duration": 1842.5,
  "text": "full transcription text...",
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "Welcome to the show."
    }
  ]
}
```

### both format
Write both `.txt` and `.json` files.

## Core Transcription Logic (`transcriber.py`)

Wrap `mlx_whisper.transcribe()`:

```python
import mlx_whisper

def transcribe_file(
    file_path: str,
    model: str = "mlx-community/whisper-large-v3-turbo",
    language: str | None = None,
) -> dict:
    """
    Returns the full mlx_whisper result dict with 'text' and 'segments'.
    """
    result = mlx_whisper.transcribe(
        file_path,
        path_or_hf_repo=model,
        language=language,
    )
    return result
```

## Design Principles

1. **Resumable** — Interrupted runs pick up where they left off via SQLite tracker
2. **Observable** — Rich progress bars and a `status` command to check on jobs
3. **Simple to verify** — `single` command for quick spot-checks before committing to a batch
4. **No external services** — Everything runs locally, no API keys, no network calls (after initial model download)
5. **Mirrors directory structure** — Output directory structure matches input, making it easy to correlate files

## Testing Notes

- `test_scanner.py` — Test file discovery with mixed file types, nested directories, case-insensitive extension matching
- `test_tracker.py` — Test SQLite CRUD, status transitions, resume logic
- `test_transcriber.py` — Can be skipped in CI (requires model download); include a small fixture audio file for local testing

## Future Considerations (Out of Scope for v1)

- Speaker diarization via WhisperX
- Post-processing with a local LLM (cleanup, summarization)
- Web UI for reviewing transcriptions
- Export to SRT/VTT subtitle formats