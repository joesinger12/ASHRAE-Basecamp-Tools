from __future__ import annotations

import os
from pathlib import Path

from basecamp import Client

DEFAULT_ACCOUNT_ID = "3106353"
TOKEN_ENV = "BASECAMP_TOKEN"
ACCOUNT_ENV = "BASECAMP_ACCOUNT_ID"
USER_AGENT = "ASHRAE-Basecamp-Tools (joe.singer@noresco.com)"


class ConfigError(Exception):
    pass


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_settings() -> tuple[str, str]:
    load_dotenv()
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise ConfigError(
            f"{TOKEN_ENV} is not set. Copy .env.example to .env and add a Basecamp token."
        )
    account_id = os.environ.get(ACCOUNT_ENV, DEFAULT_ACCOUNT_ID).strip() or DEFAULT_ACCOUNT_ID
    return token, account_id


def connect(
    *,
    token: str | None = None,
    account_id: str | int | None = None,
) -> tuple[Client, object]:
    settings_token, settings_account = load_settings()
    access_token = token or settings_token
    resolved_account = str(account_id) if account_id is not None else settings_account
    client = Client(access_token=access_token, user_agent=USER_AGENT)
    return client, client.for_account(resolved_account)
