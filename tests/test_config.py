"""Tests for configuration management."""

import json
import pathlib

import pytest

from companion.config import get_data_dir, initialize_directories, load_config, save_config
from companion.models import Config


def test_load_config_missing_file(tmp_path, monkeypatch):
    """Test load_config returns defaults when file doesn't exist."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config = load_config()

    assert isinstance(config, Config)
    # Config uses default data directory ending in .companion
    assert config.data_directory.name == ".companion"
    assert config.model_name == "Qwen/Qwen2.5-1.5B"
    assert config.first_run_complete is False


def test_load_config_existing_file(tmp_path, monkeypatch):
    """Test load_config reads existing config file."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config_dir = tmp_path / ".companion"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    test_config = {
        "data_directory": str(tmp_path / "custom_data"),
        "model_name": "test-model",
        "max_prompt_tokens": 200,
        "first_run_complete": True,
        "enable_encryption": False,
    }

    with config_file.open("w") as f:
        json.dump(test_config, f)

    config = load_config()

    assert config.data_directory == tmp_path / "custom_data"
    assert config.model_name == "test-model"
    assert config.max_prompt_tokens == 200
    assert config.first_run_complete is True
    assert config.enable_encryption is False


def test_load_config_invalid_json(tmp_path, monkeypatch):
    """Test load_config raises ValueError for invalid JSON."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config_dir = tmp_path / ".companion"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_file.write_text("{ invalid json }")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_config()


def test_save_config(tmp_path, monkeypatch):
    """Test save_config creates file with correct content."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(
        data_directory=tmp_path / "test_data",
        model_name="custom-model",
        first_run_complete=True,
    )

    save_config(config)

    config_file = tmp_path / ".companion" / "config.json"
    assert config_file.exists()

    with config_file.open() as f:
        saved_data = json.load(f)

    assert saved_data["model_name"] == "custom-model"
    assert saved_data["first_run_complete"] is True
    assert saved_data["data_directory"] == str(tmp_path / "test_data")


def test_save_config_creates_directory(tmp_path, monkeypatch):
    """Test save_config creates config directory if needed."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config_dir = tmp_path / ".companion"
    assert not config_dir.exists()

    config = Config()
    save_config(config)

    assert config_dir.exists()
    assert (config_dir / "config.json").exists()


def test_get_data_dir_creates_directory(tmp_path, monkeypatch):
    """Test get_data_dir creates data directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Set custom data directory
    custom_data = tmp_path / "custom_companion"
    config = Config(data_directory=custom_data)
    save_config(config)

    assert not custom_data.exists()

    data_dir = get_data_dir()

    assert data_dir == custom_data
    assert data_dir.exists()


def test_get_data_dir_uses_existing_directory(tmp_path, monkeypatch):
    """Test get_data_dir returns existing directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    custom_data = tmp_path / "existing_data"
    custom_data.mkdir(parents=True)

    config = Config(data_directory=custom_data)
    save_config(config)

    data_dir = get_data_dir()

    assert data_dir == custom_data
    assert data_dir.exists()


def test_initialize_directories(tmp_path, monkeypatch):
    """Test initialize_directories creates all required subdirectories."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(data_directory=tmp_path / "data")
    save_config(config)

    initialize_directories()

    data_dir = tmp_path / "data"
    assert (data_dir / "entries").exists()
    assert (data_dir / "analysis").exists()
    assert (data_dir / "models").exists()
    assert (data_dir / "audit").exists()


def test_initialize_directories_idempotent(tmp_path, monkeypatch):
    """Test initialize_directories can be called multiple times safely."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config = Config(data_directory=tmp_path / "data")
    save_config(config)

    # Call twice
    initialize_directories()
    initialize_directories()

    # Should still have all directories
    data_dir = tmp_path / "data"
    assert (data_dir / "entries").exists()
    assert (data_dir / "analysis").exists()
    assert (data_dir / "models").exists()
    assert (data_dir / "audit").exists()
