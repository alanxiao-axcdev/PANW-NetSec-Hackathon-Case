"""Configuration management for Companion.

Handles loading and saving application configuration, directory initialization,
and path management.
"""

import json
import logging
from pathlib import Path

from companion.models import Config

logger = logging.getLogger(__name__)


def load_config() -> Config:
    """Load configuration from file or return defaults.

    Loads configuration from ~/.companion/config.json if it exists.
    If the file doesn't exist, returns default configuration.

    Returns:
        Config object with loaded or default settings

    Raises:
        ValueError: If config file exists but contains invalid data
    """
    config_path = Path.home() / ".companion" / "config.json"

    if not config_path.exists():
        logger.debug("Config file not found, using defaults")
        return Config()

    try:
        with config_path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Convert data_directory string to Path if present
        if "data_directory" in data and isinstance(data["data_directory"], str):
            data["data_directory"] = Path(data["data_directory"])

        config = Config(**data)
        logger.info("Loaded configuration from %s", config_path)
        return config

    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in config file: {e}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to load config: {e}"
        raise ValueError(msg) from e


def save_config(config: Config) -> None:
    """Save configuration to file.

    Saves configuration to ~/.companion/config.json, creating directories
    if needed. Converts Path objects to strings for JSON serialization.

    Args:
        config: Configuration object to save

    Raises:
        OSError: If unable to create directories or write file
    """
    config_path = Path.home() / ".companion" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and handle Path serialization
    config_dict = config.model_dump()
    if "data_directory" in config_dict:
        config_dict["data_directory"] = str(config_dict["data_directory"])

    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        logger.info("Saved configuration to %s", config_path)
    except OSError as e:
        logger.error("Failed to save config: %s", e)
        raise


def get_data_dir() -> Path:
    """Get data directory path, create if doesn't exist.

    Returns the data directory from current configuration, creating
    the directory if it doesn't exist.

    Returns:
        Path to data directory

    Raises:
        OSError: If unable to create directory
    """
    config = load_config()
    data_dir = config.data_directory

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Data directory: %s", data_dir)
        return data_dir
    except OSError as e:
        logger.error("Failed to create data directory %s: %s", data_dir, e)
        raise


def initialize_directories() -> None:
    """Create all required directories (entries, analysis, models, audit).

    Creates the complete directory structure needed for Companion:
    - data_directory/entries: Journal entries
    - data_directory/analysis: Analysis results
    - data_directory/models: Downloaded AI models
    - data_directory/audit: Security audit logs

    Raises:
        OSError: If unable to create directories
    """
    data_dir = get_data_dir()

    subdirs = ["entries", "analysis", "models", "audit"]

    for subdir in subdirs:
        dir_path = data_dir / subdir
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Initialized directory: %s", dir_path)
        except OSError as e:
            logger.error("Failed to create directory %s: %s", dir_path, e)
            raise

    logger.info("Initialized all directories under %s", data_dir)
