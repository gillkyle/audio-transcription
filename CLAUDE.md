# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local-first CLI tool for batch transcribing audio/video files using `mlx-whisper` on Apple Silicon. See `SPEC.md` for the full specification.

## Development Commands

This project uses **uv** for Python project management. All commands should be run via `uv run`.

```bash
# Install dependencies
uv sync

# Run the CLI
uv run transcribe <command>

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_scanner.py

# Run a single test
uv run pytest tests/test_scanner.py::test_function_name -v
```

## Architecture

The project is in early development. The target architecture (from SPEC.md) is:

- **`src/transcribe_cli/cli.py`** — Typer CLI entrypoint. Defines commands: `run`, `single`, `status`, `retry`, `list`. Registered as `transcribe` script in pyproject.toml.
- **`src/transcribe_cli/transcriber.py`** — Wraps `mlx_whisper.transcribe()`. Returns dict with `text` and `segments`.
- **`src/transcribe_cli/tracker.py`** — SQLite-based job tracker stored at `<output_dir>/.transcribe-cli/jobs.db`. Tracks file status (`pending` → `processing` → `completed`/`failed`) to enable resume of interrupted runs.
- **`src/transcribe_cli/scanner.py`** — Recursive file discovery. Matches audio (`.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`) and video (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`) extensions, case-insensitive.
- **`src/transcribe_cli/config.py`** — Default settings including model config.

## Key Design Decisions

- **Resumable runs**: The SQLite tracker means interrupted batch jobs pick up where they left off. Always update file status atomically.
- **Directory mirroring**: Output directory structure mirrors input (e.g., `input/podcast/ep01.mp3` → `output/podcast/ep01.txt`).
- **No external services**: Everything runs locally after initial model download. No API keys needed.
- **Default model**: `mlx-community/whisper-large-v3-turbo`

## Stack

- Python 3.12+, uv, mlx-whisper, typer, rich, SQLite (stdlib)
