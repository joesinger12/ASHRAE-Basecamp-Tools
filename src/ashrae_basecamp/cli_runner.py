from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

DEFAULT_ACCOUNT_ID = "3106353"
DEFAULT_PROJECT_ID = "352581"


class CliError(Exception):
    pass


def unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "ok" in payload:
        if not payload["ok"]:
            raise CliError(str(payload.get("error") or payload.get("hint") or "basecamp command failed"))
        return payload.get("data")
    return payload


def run_basecamp(
    *args: str,
    stdin: str | None = None,
) -> Any:
    binary = shutil.which("basecamp")
    if not binary:
        raise CliError(
            "Official Basecamp CLI not found. See docs/SETUP.md: install it, then run `basecamp auth login`."
        )
    cmd = [binary, *args]
    if "--json" not in args:
        cmd.append("--json")
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            input=stdin,
        )
    except OSError as exc:
        raise CliError(f"Could not run basecamp: {exc}") from exc
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise CliError(err or f"basecamp exited {completed.returncode}")
    raw = completed.stdout.strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"basecamp returned non-JSON output: {raw[:200]}") from exc
    return unwrap(payload)
