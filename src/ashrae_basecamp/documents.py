from __future__ import annotations

from typing import Any

from ashrae_basecamp.content import html_fragment


def merge_document(
    current: dict[str, Any],
    *,
    title: str | None = None,
    content: str | None = None,
) -> dict[str, str]:
    """Build a full PUT body. Omitted fields keep the current values."""
    merged_title = current["title"] if title is None else title
    if content is None:
        merged_content = current.get("content") or ""
    else:
        merged_content = content
    if merged_title is None:
        raise ValueError("document title is missing")
    return {"title": str(merged_title), "content": str(merged_content)}


def append_content(current_content: str | None, fragment: str) -> str:
    existing = current_content or ""
    return existing + fragment


def get_document(account: Any, document_id: int) -> dict[str, Any]:
    return account.documents.get(document_id=document_id)


def update_document(
    account: Any,
    document_id: int,
    *,
    title: str | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    current = get_document(account, document_id)
    payload = merge_document(current, title=title, content=content)
    return account.documents.replace(document_id=document_id, **payload)


def append_document(
    account: Any,
    document_id: int,
    *,
    text: str | None = None,
    html: str | None = None,
) -> dict[str, Any]:
    fragment = html_fragment(text=text, html_body=html)
    current = get_document(account, document_id)
    payload = merge_document(current, content=append_content(current.get("content"), fragment))
    return account.documents.replace(document_id=document_id, **payload)


def create_document(
    account: Any,
    vault_id: int,
    *,
    title: str,
    content: str,
    status: str = "active",
) -> dict[str, Any]:
    return account.documents.create(
        vault_id=vault_id,
        title=title,
        content=content,
        status=status,
    )
