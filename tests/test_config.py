"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from accobot.config import (
    DEFAULT_CONFIG,
    _deep_merge,
    get_accobot_home,
    load_config,
    save_config,
)


def test_default_config_structure():
    """Default config has expected top-level keys."""
    assert "model" in DEFAULT_CONFIG
    assert "agent" in DEFAULT_CONFIG
    assert "database" in DEFAULT_CONFIG
    assert "web" in DEFAULT_CONFIG
    assert "user" in DEFAULT_CONFIG


def test_get_accobot_home_default():
    """Default home is ~/.accobot."""
    with patch.dict(os.environ, {"ACCOBOT_HOME": ""}, clear=False):
        os.environ.pop("ACCOBOT_HOME", None)
        home = get_accobot_home()
        assert home == Path.home() / ".accobot"


def test_get_accobot_home_env_override():
    """ACCOBOT_HOME env var overrides default."""
    with patch.dict(os.environ, {"ACCOBOT_HOME": "/tmp/test_accobot"}):
        home = get_accobot_home()
        assert home == Path("/tmp/test_accobot")


def test_deep_merge():
    """Deep merge correctly handles nested dicts."""
    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    override = {"a": 2, "nested": {"y": 99}, "new_key": "hello"}
    _deep_merge(base, override)
    assert base == {"a": 2, "nested": {"x": 10, "y": 99}, "new_key": "hello"}


def test_load_config_returns_defaults_when_no_file():
    """load_config returns defaults when config.yaml doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"ACCOBOT_HOME": tmpdir}):
            config = load_config()
            assert config["model"]["provider"] == "deepseek"
            assert config["model"]["model_name"] == "deepseek-chat"


def test_save_and_load_config():
    """Config can be saved and loaded back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"ACCOBOT_HOME": tmpdir}):
            config = load_config()
            config["model"]["model_name"] = "deepseek-chat"
            save_config(config)

            loaded = load_config()
            assert loaded["model"]["model_name"] == "deepseek-chat"
