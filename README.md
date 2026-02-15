# Transcribe CLI

A local-first CLI tool for batch transcribing audio/video files using [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon.

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for project management

## Install

```bash
uv sync
```

## Usage

```bash
# Transcribe a single file (outputs to stdout)
uv run transcribe single recording.mp3

# Batch transcribe a directory
uv run transcribe run ./interviews ./output

# Check progress on a batch job
uv run transcribe status ./output

# Retry any failed files
uv run transcribe retry ./output

# List all tracked files
uv run transcribe list ./output
```

### Options

```bash
uv run transcribe run <input_dir> <output_dir> \
  --model mlx-community/whisper-large-v3-turbo \
  --format txt|json|both \
  --language en \
  --overwrite
```

## Model & Weights

The default model is `mlx-community/whisper-large-v3-turbo`, an MLX-optimized Whisper variant hosted on Hugging Face.

**Weights are downloaded once and cached locally.** On the first run, mlx-whisper downloads the model weights (~3GB) from Hugging Face to `~/.cache/huggingface/hub/`. Every subsequent run loads from this local cache with no network call. If you switch to a different `--model`, that model gets downloaded once and cached the same way.

## Performance

Within a single `transcribe run` batch, the model is loaded into memory once and reused for all files — there's no per-file reload overhead.

The main performance bottlenecks, in order of impact:

1. **Inference** — The actual transcription is the bulk of wall-clock time. Speed depends on your Apple Silicon chip. The `single` command prints a real-time factor (RTF) — e.g., RTF 0.10x means 10 minutes of audio transcribes in 1 minute.
2. **Model loading** — Loading weights into memory takes a few seconds at CLI startup. This happens once per invocation.
3. **Audio decoding** — Compressed formats (MP3, AAC) have some decode overhead, but it's small relative to inference.

File scanning, SQLite tracking, and output writing are all negligible.

## Supported Formats

**Audio:** `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`
**Video:** `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`

## Resumable Runs

Batch jobs track progress in a SQLite database (`<output_dir>/.transcribe-cli/jobs.db`). If a run is interrupted, re-running the same command picks up where it left off — completed files are skipped automatically. Use `--overwrite` to force re-transcription.

## Output Structure

Output mirrors the input directory structure:

```
input/podcasts/ep01.mp3  →  output/podcasts/ep01.txt
input/interviews/q1.wav  →  output/interviews/q1.txt
```
