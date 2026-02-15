import json
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table

from .config import DEFAULT_MODEL, DEFAULT_FORMAT
from .scanner import scan_directory, compute_output_path
from .tracker import Tracker
from .transcriber import transcribe_file
from .vocabulary import load_vocabulary, build_initial_prompt, apply_replacements

app = typer.Typer(help="Batch transcribe audio/video files using mlx-whisper.")
console = Console()
err_console = Console(stderr=True)


def write_output(result: dict, output_path: Path, fmt: str) -> None:
    """Write transcription result to file(s)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt in ("txt", "both"):
        txt_path = output_path.with_suffix(".txt")
        txt_path.write_text(result["text"].strip() + "\n")

    if fmt in ("json", "both"):
        json_path = output_path.with_suffix(".json")
        output = {
            "file": output_path.stem,
            "text": result["text"],
            "segments": [
                {"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result.get("segments", [])
            ],
        }
        json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")


def apply_vocab_replacements(result: dict, vocab: dict | None) -> dict:
    """Apply vocabulary replacements to transcription result text and segments."""
    if not vocab:
        return result
    result["text"] = apply_replacements(result["text"], vocab)
    for segment in result.get("segments", []):
        segment["text"] = apply_replacements(segment["text"], vocab)
    return result


@app.command()
def run(
    input_dir: Path = typer.Argument(..., help="Directory containing audio/video files"),
    output_dir: Path = typer.Argument(..., help="Directory for transcription output"),
    model: str = typer.Option(DEFAULT_MODEL, help="Whisper model to use"),
    format: str = typer.Option(DEFAULT_FORMAT, "--format", help="Output format: txt, json, or both"),
    language: str = typer.Option(None, help="Language code (e.g. 'en'). Default: auto-detect"),
    overwrite: bool = typer.Option(False, help="Re-transcribe completed files"),
    vocab: Path = typer.Option(None, "--vocab", help="Path to vocabulary JSON file (default: auto-discover from output_dir)"),
):
    """Batch transcribe all audio/video files in a directory."""
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if not input_dir.is_dir():
        console.print(f"[red]Input directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    vocabulary = load_vocabulary(vocab_path=vocab, output_dir=output_dir)
    initial_prompt = build_initial_prompt(vocabulary)

    files = scan_directory(input_dir)
    if not files:
        console.print("[yellow]No supported audio/video files found.[/yellow]")
        raise typer.Exit(0)

    tracker = Tracker(output_dir)

    # Register all files in tracker
    for f in files:
        out_path = compute_output_path(f, input_dir, output_dir, format)
        tracker.add_file(str(f), str(out_path), model)

    # Determine which files to process
    to_process = []
    for f in files:
        status = tracker.get_status(str(f))
        if overwrite or status != "completed":
            to_process.append(f)

    if not to_process:
        console.print("[green]All files already transcribed.[/green]")
        tracker.close()
        raise typer.Exit(0)

    console.print(f"Processing {len(to_process)} of {len(files)} files with model [bold]{model}[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Transcribing", total=len(to_process))

        for f in to_process:
            progress.update(task, description=f"[cyan]{f.name}[/cyan]")
            out_path = compute_output_path(f, input_dir, output_dir, format)
            tracker.mark_processing(str(f))

            try:
                start = time.time()
                result = transcribe_file(str(f), model=model, language=language, initial_prompt=initial_prompt)
                elapsed = time.time() - start

                apply_vocab_replacements(result, vocabulary)
                write_output(result, out_path, format)

                duration = result.get("duration") or result.get("segments", [{}])[-1].get("end")
                tracker.mark_completed(str(f), duration_seconds=duration, processing_seconds=elapsed)
            except Exception as e:
                tracker.mark_failed(str(f), str(e))
                console.print(f"[red]Failed: {f.name} — {e}[/red]")

            progress.advance(task)

    tracker.close()
    console.print("[green]Done![/green]")


@app.command()
def single(
    file_path: Path = typer.Argument(..., help="Audio/video file to transcribe"),
    model: str = typer.Option(DEFAULT_MODEL, help="Whisper model to use"),
    output: Path = typer.Option(None, help="Output file path (default: stdout)"),
    format: str = typer.Option(DEFAULT_FORMAT, "--format", help="Output format: txt or json"),
    language: str = typer.Option(None, help="Language code (e.g. 'en'). Default: auto-detect"),
    vocab: Path = typer.Option(None, "--vocab", help="Path to vocabulary JSON file"),
):
    """Transcribe a single file for quick testing."""
    file_path = file_path.resolve()
    if not file_path.is_file():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    vocabulary = load_vocabulary(vocab_path=vocab)
    initial_prompt = build_initial_prompt(vocabulary)

    err_console.print(f"Transcribing [bold]{file_path.name}[/bold] with model [bold]{model}[/bold]...")

    start = time.time()
    result = transcribe_file(str(file_path), model=model, language=language, initial_prompt=initial_prompt)
    elapsed = time.time() - start

    apply_vocab_replacements(result, vocabulary)
    duration = result.get("duration")

    if output:
        write_output(result, output, format)
        err_console.print(f"[green]Written to {output}[/green]")
    else:
        if format == "json":
            out = {
                "file": file_path.name,
                "text": result["text"],
                "segments": [
                    {"start": s["start"], "end": s["end"], "text": s["text"]}
                    for s in result.get("segments", [])
                ],
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(result["text"].strip())

    # Print timing to stderr
    rtf = elapsed / duration if duration else None
    err_console.print(f"Duration: {duration:.1f}s | Processing: {elapsed:.1f}s | RTF: {rtf:.2f}x" if duration and rtf else f"Processing: {elapsed:.1f}s")


@app.command()
def status(
    output_dir: Path = typer.Argument(..., help="Output directory with tracker DB"),
):
    """Show progress for a batch job."""
    output_dir = output_dir.resolve()
    tracker = Tracker(output_dir)
    summary = tracker.get_summary()

    if summary["total"] == 0:
        console.print("[yellow]No files tracked yet.[/yellow]")
        tracker.close()
        return

    table = Table(title="Transcription Status")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total files", str(summary["total"]))
    table.add_row("Completed", f"[green]{summary['completed']}[/green]")
    table.add_row("Pending", str(summary["pending"]))
    table.add_row("Processing", str(summary["processing"]))
    table.add_row("Failed", f"[red]{summary['failed']}[/red]" if summary["failed"] else "0")

    if summary["total_duration"]:
        table.add_row("Total audio duration", f"{summary['total_duration']:.1f}s")
    if summary["total_processing"]:
        table.add_row("Total processing time", f"{summary['total_processing']:.1f}s")
        if summary["total_duration"]:
            rtf = summary["total_processing"] / summary["total_duration"]
            table.add_row("Average RTF", f"{rtf:.2f}x")

    console.print(table)

    # Show failed files
    failed = tracker.get_failed_files()
    if failed:
        console.print("\n[red bold]Failed files:[/red bold]")
        for row in failed:
            console.print(f"  {row['input_path']}: {row['error']}")

    tracker.close()


@app.command()
def retry(
    output_dir: Path = typer.Argument(..., help="Output directory with tracker DB"),
    model: str = typer.Option(None, help="Model to use (default: same as original run)"),
    vocab: Path = typer.Option(None, "--vocab", help="Path to vocabulary JSON file (default: auto-discover from output_dir)"),
):
    """Retry all failed files."""
    output_dir = output_dir.resolve()

    vocabulary = load_vocabulary(vocab_path=vocab, output_dir=output_dir)
    initial_prompt = build_initial_prompt(vocabulary)

    tracker = Tracker(output_dir)

    count = tracker.reset_failed()
    if count == 0:
        console.print("[green]No failed files to retry.[/green]")
        tracker.close()
        return

    console.print(f"Retrying {count} failed files...")

    pending = tracker.get_pending_files()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Retrying", total=len(pending))

        for row in pending:
            input_path = row["input_path"]
            out_path = Path(row["output_path"])
            file_model = model or row["model"]
            progress.update(task, description=f"[cyan]{Path(input_path).name}[/cyan]")
            tracker.mark_processing(input_path)

            try:
                start = time.time()
                result = transcribe_file(input_path, model=file_model, initial_prompt=initial_prompt)
                elapsed = time.time() - start

                apply_vocab_replacements(result, vocabulary)
                write_output(result, out_path, out_path.suffix.lstrip(".") or "txt")

                duration = result.get("duration") or result.get("segments", [{}])[-1].get("end")
                tracker.mark_completed(input_path, duration_seconds=duration, processing_seconds=elapsed)
            except Exception as e:
                tracker.mark_failed(input_path, str(e))
                console.print(f"[red]Failed again: {Path(input_path).name} — {e}[/red]")

            progress.advance(task)

    tracker.close()
    console.print("[green]Retry complete![/green]")


@app.command("list")
def list_files(
    output_dir: Path = typer.Argument(..., help="Output directory with tracker DB"),
    status_filter: str = typer.Option(None, "--status", help="Filter by status: pending, processing, completed, failed"),
    sort: str = typer.Option("name", help="Sort by: name, status, duration"),
):
    """List all tracked files and their statuses."""
    output_dir = output_dir.resolve()
    tracker = Tracker(output_dir)
    files = tracker.get_all_files(status=status_filter, sort=sort)

    if not files:
        console.print("[yellow]No files found.[/yellow]")
        tracker.close()
        return

    table = Table(title="Tracked Files")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Processing", justify="right")

    for row in files:
        name = Path(row["input_path"]).name
        st = row["status"]
        style = {"completed": "green", "failed": "red", "processing": "yellow"}.get(st, "")
        dur = f"{row['duration_seconds']:.1f}s" if row["duration_seconds"] else "-"
        proc = f"{row['processing_seconds']:.1f}s" if row["processing_seconds"] else "-"
        table.add_row(name, f"[{style}]{st}[/{style}]" if style else st, dur, proc)

    console.print(table)
    tracker.close()


def main():
    app()
