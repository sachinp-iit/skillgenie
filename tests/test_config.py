"""
Tests for the SkillGenie configuration loader.
"""

import os

import pytest

from skillgenie.config import DEFAULT_CONFIG, Config


def test_creates_config_file_when_missing(tmp_path):
    path = tmp_path / "config.json"

    config = Config(str(path))

    assert path.exists()

    assert config.get("database.url") == DEFAULT_CONFIG["database"]["url"]

    assert config.get("embeddings.provider") == "sentence-transformers"


def test_loads_existing_values(tmp_path):
    import json

    path = tmp_path / "config.json"

    path.write_text(
        json.dumps(
            {
                "database": {"url": "postgresql://user:pw@db:5432/x"},
                "similarity": {"threshold": 0.75},
            }
        ),
        encoding="utf-8",
    )

    config = Config(str(path))

    assert config.get("database.url") == "postgresql://user:pw@db:5432/x"

    assert config.get("similarity.threshold") == 0.75

    # Unspecified keys fall back to defaults
    assert config.get("embeddings.provider") == "sentence-transformers"


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "hash")

    config = Config(str(tmp_path / "config.json"))

    assert config.get("embeddings.provider") == "hash"


def test_get_type_helpers(monkeypatch, tmp_path):
    monkeypatch.setenv("LEARNING_AUTO_APPROVAL", "true")
    monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.88")

    config = Config(str(tmp_path / "config.json"))

    assert config.get_bool("learning.auto_approval") is True
    assert config.get_bool("missing.key") is False
    assert config.get_bool("missing.key", True) is True
    assert config.get_float("similarity.threshold") == 0.88
    assert config.get_float("missing") == 0.0
    assert config.get_float("missing", 1.5) == 1.5

    assert config.get_int("monitoring.interval_seconds") == 60


def test_missing_key_returns_default(tmp_path):
    config = Config(str(tmp_path / "config.json"))

    assert config.get("does.not.exist") is None

    assert config.get("does.not.exist", "fallback") == "fallback"


def test_as_dict_and_config_file(tmp_path):
    path = tmp_path / "config.json"

    config = Config(str(path))

    assert config.as_dict["logging"]["level"] == "INFO"

    assert str(config.config_file.resolve()) == str(path.resolve())


def test_invalid_config_json_falls_back(tmp_path):
    import json

    path = tmp_path / "config.json"

    path.write_text("{ not valid json ", encoding="utf-8")

    with pytest.raises((json.JSONDecodeError, ValueError)):
        _ = Config(str(path))