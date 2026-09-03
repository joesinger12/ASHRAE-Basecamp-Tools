from __future__ import annotations

from typing import Any

from ashrae_basecamp.cli_runner import DEFAULT_PROJECT_ID, run_basecamp
from ashrae_basecamp.content import html_fragment
from ashrae_basecamp.urls import document_id_from, parse_basecamp_url


def append_content(current_content: str | None, fragment: str) -> str:
    return (current_content or "") + fragment


def _project_id(target: str, doc: dict[str, Any] | None = None) -> str:
    ref = parse_basecamp_url(target)
    if ref.bucket_id is not None:
        return str(ref.bucket_id)
    if doc:
        bucket = doc.get("bucket") or {}
        if bucket.get("id"):
            return str(bucket["id"])
    return DEFAULT_PROJECT_ID


def show_document(target: str) -> dict[str, Any]:
    ref = parse_basecamp_url(target)
    document_id = document_id_from(target)
    data = run_basecamp(
        "files",
        "show",
        str(document_id),
        "--in",
        _project_id(target),
    )
    if not isinstance(data, dict):
        raise TypeError(f"Unexpected files show payload for {ref.resource_id}")
    return data


def append_document(
    target: str,
    *,
    text: str | None = None,
    html: str | None = None,
) -> dict[str, Any]:
    fragment = html_fragment(text=text, html_body=html)
    current = show_document(target)
    new_content = append_content(current.get("content"), fragment)
    document_id = current.get("id") or document_id_from(target)
    data = run_basecamp(
        "files",
        "update",
        str(document_id),
        "--content",
        "-",
        "--in",
        _project_id(target, current),
        stdin=new_content,
    )
    if isinstance(data, dict):
        return data
    return show_document(target)
