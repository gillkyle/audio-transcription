from pathlib import Path

from .config import SUPPORTED_EXTENSIONS


def scan_directory(input_dir: Path) -> list[Path]:
    """Recursively scan input_dir for supported audio/video files."""
    files = []
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def compute_output_path(
    input_file: Path, input_dir: Path, output_dir: Path, fmt: str
) -> Path:
    """Compute output path mirroring the input directory structure."""
    relative = input_file.relative_to(input_dir)
    ext = ".json" if fmt == "json" else ".txt"
    return output_dir / relative.with_suffix(ext)
