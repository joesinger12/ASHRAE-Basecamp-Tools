from pathlib import Path

from ashrae_basecamp.client import write_env_value


def test_write_env_value_creates_and_updates(tmp_path: Path):
    path = tmp_path / ".env"
    write_env_value(path, "BASECAMP_TOKEN", "first")
    assert path.read_text(encoding="utf-8") == "BASECAMP_TOKEN=first\n"
    write_env_value(path, "BASECAMP_ACCOUNT_ID", "3106353")
    write_env_value(path, "BASECAMP_TOKEN", "second")
    text = path.read_text(encoding="utf-8")
    assert "BASECAMP_TOKEN=second" in text
    assert "BASECAMP_TOKEN=first" not in text
    assert "BASECAMP_ACCOUNT_ID=3106353" in text
