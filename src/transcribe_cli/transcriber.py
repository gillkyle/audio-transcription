import mlx_whisper

from .config import DEFAULT_MODEL


def transcribe_file(
    file_path: str,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
) -> dict:
    """Transcribe a single audio/video file using mlx-whisper.

    Returns the full mlx_whisper result dict with 'text' and 'segments'.
    """
    kwargs = {
        "path_or_hf_repo": model,
    }
    if language:
        kwargs["language"] = language

    result = mlx_whisper.transcribe(file_path, **kwargs)
    return result
