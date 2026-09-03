from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from basecamp.errors import BasecampError

from ashrae_basecamp.client import ConfigError, connect
from ashrae_basecamp.content import document_brief, extract_links, html_fragment, html_to_text
from ashrae_basecamp.documents import append_document, get_document, update_document
from ashrae_basecamp.urls import UrlError, document_id_from, parse_basecamp_url


def _die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def _read_input(file: str | None) -> str:
    if file is None or file == "-":
        return sys.stdin.read()
    return Path(file).read_text(encoding="utf-8")


def _account_for(url_or_id: str, default_account: str | int) -> tuple[Any, Any, int]:
    ref = parse_basecamp_url(url_or_id)
    account_id = ref.account_id if ref.account_id is not None else default_account
    client, account = connect(account_id=account_id)
    return client, account, document_id_from(url_or_id)


def cmd_whoami(_args: argparse.Namespace) -> int:
    client, account = connect()
    info = client.authorization.get()
    identity = info.get("identity") or {}
    print(f"account: {account.account_id}")
    name = " ".join(part for part in (identity.get("first_name"), identity.get("last_name")) if part)
    if name:
        print(f"name: {name}")
    if identity.get("email_address"):
        print(f"email: {identity['email_address']}")
    if info.get("expires_at"):
        print(f"expires_at: {info['expires_at']}")
    accounts = [a for a in info.get("accounts") or [] if a.get("product") == "bc3"]
    if accounts:
        print("accounts:")
        for item in accounts:
            print(f"  {item.get('id')}: {item.get('name')}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    _, default_account = _settings()
    _client, account, document_id = _account_for(args.target, default_account)
    doc = get_document(account, document_id)
    if args.format == "json":
        json.dump(doc, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.format == "html":
        sys.stdout.write(doc.get("content") or "")
        if not (doc.get("content") or "").endswith("\n"):
            sys.stdout.write("\n")
    else:
        sys.stdout.write(html_to_text(doc.get("content") or ""))
        sys.stdout.write("\n")
    return 0


def cmd_put(args: argparse.Namespace) -> int:
    _, default_account = _settings()
    _client, account, document_id = _account_for(args.target, default_account)
    body = _read_input(args.file)
    if args.text:
        body = html_fragment(text=body)
    update_document(account, document_id, title=args.title, content=body)
    print(f"updated document {document_id}")
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    _, default_account = _settings()
    _client, account, document_id = _account_for(args.target, default_account)
    if args.text is not None:
        append_document(account, document_id, text=args.text)
    else:
        append_document(account, document_id, html=_read_input(args.file))
    print(f"appended to document {document_id}")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    _, default_account = _settings()
    _client, account, document_id = _account_for(args.target, default_account)
    doc = get_document(account, document_id)
    for link in extract_links(doc.get("content") or ""):
        if link.text:
            print(f"{link.text}: {link.href}")
        else:
            print(link.href)
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    _, default_account = _settings()
    _client, account, document_id = _account_for(args.target, default_account)
    doc = get_document(account, document_id)
    sys.stdout.write(document_brief(doc))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    _client, account = connect()
    kwargs: dict[str, Any] = {"q": args.query}
    if args.type:
        kwargs["type_names"] = [args.type]
    if args.project:
        kwargs["bucket_ids"] = [int(args.project)]
    results = account.search.search(**kwargs)
    for item in results:
        title = item.get("title") or item.get("subject") or ""
        kind = item.get("type") or ""
        url = item.get("app_url") or ""
        print(f"{kind}\t{title}\t{url}")
    return 0


def _settings() -> tuple[str, str]:
    from ashrae_basecamp.client import load_settings

    return load_settings()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ashrae-bc", description="ASHRAE Basecamp tools")
    sub = parser.add_subparsers(dest="command", required=True)

    whoami = sub.add_parser("whoami", help="Show the authenticated Basecamp identity")
    whoami.set_defaults(func=cmd_whoami)

    get_p = sub.add_parser("get", help="Fetch a document")
    get_p.add_argument("target", help="Document URL or id")
    get_p.add_argument("--format", choices=("json", "html", "text"), default="json")
    get_p.set_defaults(func=cmd_get)

    put_p = sub.add_parser("put", help="Replace document content (keeps title unless --title)")
    put_p.add_argument("target", help="Document URL or id")
    put_p.add_argument("--file", default="-", help="HTML file, or - for stdin")
    put_p.add_argument("--text", action="store_true", help="Treat input as plain text")
    put_p.add_argument("--title", help="New title")
    put_p.set_defaults(func=cmd_put)

    append_p = sub.add_parser("append", help="Append text or HTML to a document")
    append_p.add_argument("target", help="Document URL or id")
    append_p.add_argument("--text", help="Plain text to append")
    append_p.add_argument("--file", help="HTML file to append, or - for stdin")
    append_p.set_defaults(func=cmd_append)

    links_p = sub.add_parser("links", help="List links in a document")
    links_p.add_argument("target", help="Document URL or id")
    links_p.set_defaults(func=cmd_links)

    brief_p = sub.add_parser("brief", help="Title, URL, excerpt, and links for a document")
    brief_p.add_argument("target", help="Document URL or id")
    brief_p.set_defaults(func=cmd_brief)

    search_p = sub.add_parser("search", help="Search Basecamp")
    search_p.add_argument("query")
    search_p.add_argument("--type", help="Recording type, e.g. Document")
    search_p.add_argument("--project", help="Project / bucket id")
    search_p.set_defaults(func=cmd_search)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "append" and args.text is None and args.file is None:
        parser.error("append requires --text or --file")
    try:
        return args.func(args)
    except (ConfigError, UrlError, BasecampError) as exc:
        _die(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
