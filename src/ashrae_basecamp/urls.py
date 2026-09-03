from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

_APP_PATH = re.compile(
    r"^/(?P<account>\d+)/buckets/(?P<bucket>\d+)/(?P<kind>[a-z_]+)/(?P<id>\d+)/?$",
    re.IGNORECASE,
)
_API_SCOPED = re.compile(
    r"^/(?P<account>\d+)/buckets/(?P<bucket>\d+)/(?P<kind>[a-z_]+)/(?P<id>\d+)(?:\.json)?/?$",
    re.IGNORECASE,
)
_API_FLAT = re.compile(
    r"^/(?P<account>\d+)/(?P<kind>[a-z_]+)/(?P<id>\d+)(?:\.json)?/?$",
    re.IGNORECASE,
)
_KIND_ALIASES = {
    "document": "documents",
    "documents": "documents",
    "vault": "vaults",
    "vaults": "vaults",
    "message": "messages",
    "messages": "messages",
    "comment": "comments",
    "comments": "comments",
    "recording": "recordings",
    "recordings": "recordings",
    "upload": "uploads",
    "uploads": "uploads",
    "todolist": "todolists",
    "todolists": "todolists",
    "todo": "todos",
    "todos": "todos",
}


@dataclass(frozen=True)
class BasecampRef:
    account_id: int | None
    bucket_id: int | None
    kind: str | None
    resource_id: int


class UrlError(ValueError):
    pass


def parse_basecamp_url(value: str) -> BasecampRef:
    raw = value.strip()
    if re.fullmatch(r"\d+", raw):
        return BasecampRef(account_id=None, bucket_id=None, kind=None, resource_id=int(raw))

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        path = parsed.path
        host = parsed.netloc.lower()
        if "basecampapi.com" in host:
            match = _API_SCOPED.match(path) or _API_FLAT.match(path)
        elif "basecamp.com" in host:
            match = _APP_PATH.match(path)
        else:
            match = None
        if match is None:
            raise UrlError(f"Not a Basecamp document/resource URL: {value}")
        groups = match.groupdict()
        kind = _KIND_ALIASES.get(groups["kind"].lower(), groups["kind"].lower())
        return BasecampRef(
            account_id=int(groups["account"]),
            bucket_id=int(groups["bucket"]) if groups.get("bucket") else None,
            kind=kind,
            resource_id=int(groups["id"]),
        )

    raise UrlError(f"Not a Basecamp URL or numeric id: {value}")


def document_id_from(value: str) -> int:
    ref = parse_basecamp_url(value)
    if ref.kind not in (None, "documents"):
        raise UrlError(f"Expected a document URL or id, got {ref.kind}: {value}")
    return ref.resource_id
