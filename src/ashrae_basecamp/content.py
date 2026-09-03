from __future__ import annotations

from html.parser import HTMLParser
from dataclasses import dataclass
import html
import re


@dataclass(frozen=True)
class Link:
    href: str
    text: str


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[Link] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        text = "".join(self._parts).strip()
        self.links.append(Link(href=self._href, text=text))
        self._href = None
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "h1", "li", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "h1", "li", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def extract_links(content: str) -> list[Link]:
    parser = _LinkParser()
    parser.feed(content or "")
    parser.close()
    seen: set[str] = set()
    unique: list[Link] = []
    for link in parser.links:
        if link.href in seen:
            continue
        seen.add(link.href)
        unique.append(link)
    return unique


def html_to_text(content: str) -> str:
    parser = _TextParser()
    parser.feed(content or "")
    parser.close()
    text = "".join(parser.parts)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def text_to_html(text: str) -> str:
    escaped = html.escape(text)
    return escaped.replace("\n", "<br>")


def html_fragment(text: str | None = None, html_body: str | None = None) -> str:
    if html_body is not None:
        return html_body
    if text is None:
        raise ValueError("Provide text or HTML content")
    return f"<div>{text_to_html(text)}</div>"


def document_brief(doc: dict, *, excerpt_chars: int = 400) -> str:
    title = str(doc.get("title") or "")
    app_url = str(doc.get("app_url") or "")
    content = str(doc.get("content") or "")
    excerpt = html_to_text(content)
    if len(excerpt) > excerpt_chars:
        excerpt = excerpt[:excerpt_chars].rstrip() + "…"
    lines = [f"Title: {title}", f"URL: {app_url}", ""]
    if excerpt:
        lines.extend([excerpt, ""])
    links = extract_links(content)
    if links:
        lines.append("Links:")
        for link in links:
            if link.text:
                lines.append(f"{link.text}: {link.href}")
            else:
                lines.append(link.href)
    return "\n".join(lines).rstrip() + "\n"
