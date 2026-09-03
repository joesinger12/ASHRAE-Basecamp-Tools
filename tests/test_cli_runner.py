from ashrae_basecamp.cli_runner import CliError, unwrap
from ashrae_basecamp.cli_runner import run_basecamp
from unittest.mock import patch
import pytest


def test_unwrap_success_envelope():
    assert unwrap({"ok": True, "data": {"id": 1}}) == {"id": 1}


def test_unwrap_error_envelope():
    with pytest.raises(CliError, match="nope"):
        unwrap({"ok": False, "error": "nope"})


def test_unwrap_raw_payload():
    assert unwrap({"id": 1, "title": "Doc"}) == {"id": 1, "title": "Doc"}


def test_run_basecamp_requires_binary():
    with patch("ashrae_basecamp.cli_runner.shutil.which", return_value=None):
        with pytest.raises(CliError, match="not found"):
            run_basecamp("auth", "status")
