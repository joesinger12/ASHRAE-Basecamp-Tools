from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from basecamp import Client

DEFAULT_ACCOUNT_ID = "3106353"
TOKEN_ENV = "BASECAMP_TOKEN"
ACCOUNT_ENV = "BASECAMP_ACCOUNT_ID"
USER_AGENT = "ASHRAE-Basecamp-Tools (joe.singer@noresco.com)"
BASECAMP_ORIGIN = "https://3.basecampapi.com"
AUTHORIZATION_URL = f"{BASECAMP_ORIGIN}/authorization.json"
OAUTH_CLIENT_ID = "basecamp-cli"


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
            f"{TOKEN_ENV} is not set. Run `ashrae-bc login` or copy .env.example to .env."
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


def write_env_value(path: Path, key: str, value: str) -> None:
    lines: list[str] = []
    found = False
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_authorization(client: Client) -> dict[str, Any]:
    try:
        return client.http.get_absolute(AUTHORIZATION_URL).json()
    except Exception:
        return client.authorization.get()


def login(*, env_path: Path | None = None, scope: str = "full") -> Path:
    from basecamp.oauth import DeviceFlowError, OAuthError, discover_from_resource, perform_device_login

    path = env_path or Path.cwd() / ".env"
    access_token: str | None = None

    result = discover_from_resource(BASECAMP_ORIGIN)
    if result.kind == "selected":
        config = result.selected_config()

        def show(auth: Any) -> None:
            uri = auth.verification_uri_complete or auth.verification_uri
            print("Open this URL in a browser and sign in to Basecamp there:", flush=True)
            print(f"  {uri}", flush=True)
            if not auth.verification_uri_complete:
                print(f"Enter this code: {auth.user_code}", flush=True)

        try:
            token = perform_device_login(config, OAUTH_CLIENT_ID, scope=scope, display=show)
            access_token = token.access_token
        except (DeviceFlowError, OAuthError) as exc:
            raise ConfigError(str(exc)) from exc

    if not access_token:
        access_token = _token_from_official_cli()

    if not access_token:
        raise ConfigError(
            "Basecamp does not accept a username/password in this tool, and device login "
            "is not advertised on this server. On your computer:\n"
            "  1. Install the official CLI: https://github.com/basecamp/basecamp-cli\n"
            "  2. Run: basecamp auth login\n"
            "     (browser opens; sign in with your Basecamp email/password there)\n"
            "  3. Run: basecamp auth token\n"
            "  4. Put that value in .env as BASECAMP_TOKEN, or paste it into this agent chat."
        )

    write_env_value(path, TOKEN_ENV, access_token)
    if not _env_has_key(path, ACCOUNT_ENV):
        write_env_value(path, ACCOUNT_ENV, DEFAULT_ACCOUNT_ID)
    os.environ[TOKEN_ENV] = access_token
    return path


def _token_from_official_cli() -> str | None:
    import shutil
    import subprocess

    binary = shutil.which("basecamp")
    if not binary:
        return None
    print("Using official `basecamp` CLI. A browser window should open to sign in.", flush=True)
    login_result = subprocess.run([binary, "auth", "login"], check=False)
    if login_result.returncode != 0:
        return None
    token_result = subprocess.run(
        [binary, "auth", "token"],
        check=False,
        capture_output=True,
        text=True,
    )
    token = (token_result.stdout or "").strip()
    return token or None


def _env_has_key(path: Path, key: str) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            return True
    return False
