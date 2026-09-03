from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ashrae_basecamp.cli_runner import CliError, run_basecamp
from ashrae_basecamp.content import document_brief, extract_links
from ashrae_basecamp.documents import append_document, show_document
from ashrae_basecamp.urls import UrlError


def _die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def _read_input(file: str | None) -> str:
    if file is None or file == "-":
        return sys.stdin.read()
    return Path(file).read_text(encoding="utf-8")


def cmd_doctor(_args: argparse.Namespace) -> int:
    binary = shutil.which("basecamp")
    if not binary:
        _die("basecamp CLI is not on PATH. Install it with the steps in docs/SETUP.md.")
    print(f"basecamp: {binary}")
    status = run_basecamp("auth", "status")
    if isinstance(status, dict):
        print(status)
    else:
        print(status)
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    if args.text is not None:
        append_document(args.target, text=args.text)
    else:
        append_document(args.target, html=_read_input(args.file))
    print(f"appended to {args.target}")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    doc = show_document(args.target)
    for link in extract_links(doc.get("content") or ""):
        if link.text:
            print(f"{link.text}: {link.href}")
        else:
            print(link.href)
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    doc = show_document(args.target)
    sys.stdout.write(document_brief(doc))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ashrae-bc",
        description="ASHRAE helpers on top of the official Basecamp CLI (append, links, brief).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check that the official basecamp CLI is installed and signed in")
    doctor.set_defaults(func=cmd_doctor)

    append_p = sub.add_parser("append", help="Append text or HTML to a document without replacing the rest")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "append" and args.text is None and args.file is None:
        parser.error("append requires --text or --file")
    try:
        return args.func(args)
    except (CliError, UrlError) as exc:
        _die(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
