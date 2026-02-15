import json
from pathlib import Path

from .config import TRACKER_DIR, VOCABULARY_FILE


def load_vocabulary(
    vocab_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict | None:
    """Load vocabulary from explicit path or auto-discover from output_dir.

    Returns the parsed dict or None if no vocabulary file is found.
    """
    if vocab_path:
        path = vocab_path.resolve()
        if not path.is_file():
            return None
        return json.loads(path.read_text())

    if output_dir:
        path = output_dir / TRACKER_DIR / VOCABULARY_FILE
        if path.is_file():
            return json.loads(path.read_text())

    return None


def build_initial_prompt(vocab: dict | None) -> str | None:
    """Join vocabulary list into a comma-separated initial_prompt string."""
    if not vocab:
        return None
    terms = vocab.get("vocabulary", [])
    if not terms:
        return None
    return ", ".join(terms)


def apply_replacements(text: str, vocab: dict | None) -> str:
    """Apply case-sensitive find-and-replace from vocabulary replacements."""
    if not vocab:
        return text
    replacements = vocab.get("replacements", {})
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
