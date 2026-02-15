import json
from pathlib import Path

from transcribe_cli.vocabulary import load_vocabulary, build_initial_prompt, apply_replacements


def test_load_vocabulary_explicit_path(tmp_path):
    vocab_file = tmp_path / "vocab.json"
    data = {"vocabulary": ["Orem", "Timpanogos"], "replacements": {"Oram": "Orem"}}
    vocab_file.write_text(json.dumps(data))

    result = load_vocabulary(vocab_path=vocab_file)
    assert result == data


def test_load_vocabulary_auto_discover(tmp_path):
    tracker_dir = tmp_path / ".transcribe-cli"
    tracker_dir.mkdir()
    vocab_file = tracker_dir / "vocabulary.json"
    data = {"vocabulary": ["Orem"], "replacements": {}}
    vocab_file.write_text(json.dumps(data))

    result = load_vocabulary(output_dir=tmp_path)
    assert result == data


def test_load_vocabulary_missing_file(tmp_path):
    result = load_vocabulary(vocab_path=tmp_path / "nonexistent.json")
    assert result is None


def test_load_vocabulary_no_args():
    result = load_vocabulary()
    assert result is None


def test_load_vocabulary_explicit_overrides_output_dir(tmp_path):
    """Explicit path takes priority; output_dir is not consulted."""
    explicit = tmp_path / "custom.json"
    data = {"vocabulary": ["custom"]}
    explicit.write_text(json.dumps(data))

    result = load_vocabulary(vocab_path=explicit, output_dir=tmp_path)
    assert result == data


def test_build_initial_prompt_multiple_terms():
    vocab = {"vocabulary": ["Mount Timpanogos", "Orem", "Morningside Stake Center"]}
    result = build_initial_prompt(vocab)
    assert result == "Mount Timpanogos, Orem, Morningside Stake Center"


def test_build_initial_prompt_empty_list():
    vocab = {"vocabulary": []}
    result = build_initial_prompt(vocab)
    assert result is None


def test_build_initial_prompt_missing_key():
    vocab = {"replacements": {"a": "b"}}
    result = build_initial_prompt(vocab)
    assert result is None


def test_build_initial_prompt_none():
    result = build_initial_prompt(None)
    assert result is None


def test_apply_replacements_basic():
    vocab = {"replacements": {"Steak Center": "Stake Center"}}
    result = apply_replacements("We met at the Steak Center today.", vocab)
    assert result == "We met at the Stake Center today."


def test_apply_replacements_multiple():
    vocab = {"replacements": {"Oram": "Orem", "Mount Tupinogos": "Mount Timpanogos"}}
    result = apply_replacements("Oram is near Mount Tupinogos.", vocab)
    assert result == "Orem is near Mount Timpanogos."


def test_apply_replacements_case_sensitive():
    vocab = {"replacements": {"steak": "stake"}}
    result = apply_replacements("Steak center and steak center.", vocab)
    assert result == "Steak center and stake center."


def test_apply_replacements_no_match():
    vocab = {"replacements": {"XYZ": "ABC"}}
    result = apply_replacements("Nothing to replace here.", vocab)
    assert result == "Nothing to replace here."


def test_apply_replacements_none_vocab():
    result = apply_replacements("Some text.", None)
    assert result == "Some text."


def test_apply_replacements_no_replacements_key():
    vocab = {"vocabulary": ["Orem"]}
    result = apply_replacements("Some text.", vocab)
    assert result == "Some text."
