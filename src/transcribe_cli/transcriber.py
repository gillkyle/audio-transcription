import gc

import mlx.core as mx
import mlx_whisper

from .config import DEFAULT_MODEL


def transcribe_file(
    file_path: str,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
    initial_prompt: str | None = None,
) -> dict:
    """Transcribe a single audio/video file using mlx-whisper.

    Returns the full mlx_whisper result dict with 'text' and 'segments'.
    """
    kwargs = {
        "path_or_hf_repo": model,
    }
    if language:
        kwargs["language"] = language
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt

    result = mlx_whisper.transcribe(file_path, **kwargs)

    gc.collect()
    mx.metal.clear_cache()

    return result
