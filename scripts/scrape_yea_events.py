"""Pull YEA events from Region III chapter sites into data/events/events.csv."""

from __future__ import annotations

import argparse
import csv
import html
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "events" / "events.csv"
USER_AGENT = "Mozilla/5.0 (compatible; ASHRAE-YEA-events/1.0)"
EASTERN = ZoneInfo("America/New_York")
CSV_FIELDS = [
    "Chapter(s)",
    "Title",
    "Date",
    "Description",
    "Location",
    "Flyer",
    "External Link",
]

MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
DATE_RE = re.compile(rf"({MONTHS})\s+(\d{{1,2}}),\s+(\d{{4}})", re.I)
TIME_RE = re.compile(
    r"(\d{1,2}:\d{2}\s*[AP]M)(?:\s*[A-Z]{2,4})?\s*(?:to|-)\s*"
    r"(\d{1,2}:\d{2}\s*[AP]M)",
    re.I,
)
YEA_RE = re.compile(r"\bYEA\b", re.I)
YOUNG_ENGINEERS_RE = re.compile(r"Young Engineers in ASHRAE", re.I)

# Applied only to the event title and opening pitch, not speaker biographies.
CHAPTER_ALIASES: dict[str, tuple[str, ...]] = {
    "Philadelphia": (r"\bphiladelphia\b", r"\bphilly\b"),
    "Lehigh Valley": (r"\blehigh\b",),
    "Central Pennsylvania": (r"\bcentral pennsylvania\b", r"\bcentral pa\b"),
    "Pittsburgh": (r"\bpittsburgh\b",),
    "Baltimore": (r"\bbaltimore\b",),
    "National Capital": (r"\bnational capital\b", r"\bncc\b"),
    "Richmond": (r"\brichmond\b",),
    "Roanoke": (r"\broanoke\b",),
    "Anthracite": (r"\banthracite\b",),
    "Hampton Roads": (r"\bhampton roads\b",),
}


@dataclass(frozen=True)
class Chapter:
    """One Region III chapter site the scraper knows how to read."""

    number: str
    name: str
    area: str
    website: str
    platform: str
    events_url: str
    note: str = ""
    notes_url: str = ""

    def __repr__(self) -> str:
        return f"<Chapter:{self.number}:{self.name}>"


@dataclass
class Event:
    """One YEA event row before it is written to the CSV."""

    name: str
    when: date
    description: str
    location: str
    chapters: list[str]
    flyer: str
    link: str
    time_label: str = ""
    source: str = ""

    def __repr__(self) -> str:
        return f"<Event:{self.when.isoformat()}:{self.name}>"


@dataclass
class ScrapeReport:
    """Per-chapter outcome, including sites that could not be read."""

    chapter: Chapter
    events: list[Event] = field(default_factory=list)
    error: str = ""

    def __repr__(self) -> str:
        return f"<ScrapeReport:{self.chapter.name}:{len(self.events)}:{self.error}>"


class FetchError(Exception):
    """A chapter page did not return a usable response."""

    def __init__(self, url: str, status: int, detail: str) -> None:
        self.url = url
        self.status = status
        super().__init__(f"{url} ({status}): {detail[:180]}")

    def __repr__(self) -> str:
        return f"<FetchError:{self.status}:{self.url}>"


class Fetcher:
    """HTTP GET through curl so Cloudflare-fronted chapter sites respond."""

    def __init__(self) -> None:
        curl = shutil.which("curl") or shutil.which("curl.exe")
        if not curl:
            raise SystemExit("curl is required to scrape the chapter sites.")
        self._curl = curl
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"<Fetcher:{Path(self._curl).name}>"

    def get(self, url: str) -> str:
        with self._lock:
            cached = self._cache.get(url)
        if cached is not None:
            return cached
        body = self._request(url)
        with self._lock:
            self._cache[url] = body
        return body

    def _request(self, url: str) -> str:
        delay = 2.0
        last_error: FetchError | None = None
        for _attempt in range(3):
            with self._lock:
                proc = subprocess.run(
                    [
                        self._curl,
                        "-sL",
                        "--max-redirs",
                        "5",
                "--max-time",
                "25",
                        "-A",
                        USER_AGENT,
                        "-w",
                        "\n%{http_code}",
                        url,
                    ],
                    capture_output=True,
                )
                raw = proc.stdout.decode("utf-8", "replace")
                if "\n" in raw:
                    body, code_text = raw.rsplit("\n", 1)
                else:
                    body, code_text = raw, "0"
                try:
                    status = int(code_text.strip() or "0")
                except ValueError:
                    status = 0
                if status == 429 or status == 503:
                    last_error = FetchError(url, status, "rate limited")
                    time.sleep(delay)
                    delay *= 2
                    continue
                if status == 0 or status >= 400:
                    detail = proc.stderr.decode("utf-8", "replace").strip() or "request failed"
                    raise FetchError(url, status, detail)
                time.sleep(0.25)
                return body
        raise last_error or FetchError(url, 429, "rate limited")


CHAPTERS: tuple[Chapter, ...] = (
    Chapter(
        "021",
        "Philadelphia",
        "Philadelphia, PA",
        "https://ashraephilly.org",
        "starchapter",
        "https://ashraephilly.org/meetinginfo.php",
    ),
    Chapter(
        "022",
        "Central Pennsylvania",
        "York / Harrisburg, PA",
        "https://centralpaashrae.com",
        "starchapter",
        "https://centralpaashrae.com/meetinginfo.php",
    ),
    Chapter(
        "024",
        "Pittsburgh",
        "Pittsburgh, PA",
        "https://ashraepittsburgh.org",
        "squarespace",
        "https://ashraepittsburgh.org/calendar",
        notes_url="https://ashraepittsburgh.org/year-in-review",
    ),
    Chapter(
        "025",
        "Baltimore",
        "Baltimore, MD",
        "https://ashrae-balto.org",
        "starchapter",
        "https://ashrae-balto.org/meetinginfo.php",
    ),
    Chapter(
        "026",
        "National Capital",
        "Washington, DC",
        "https://nccashrae.org",
        "tribe",
        "https://nccashrae.org/wp-json/tribe/events/v1/events",
    ),
    Chapter(
        "027",
        "Hampton Roads",
        "Norfolk / Virginia Beach, VA",
        "https://ashraehrc.org",
        "unreadable",
        "https://ashraehrc.org/",
        note="The site does not complete a TLS handshake.",
    ),
    Chapter(
        "028",
        "Richmond",
        "Richmond, VA",
        "https://richmondashrae.org",
        "tribe",
        "https://richmondashrae.org/wp-json/tribe/events/v1/events",
    ),
    Chapter(
        "098",
        "Lehigh Valley",
        "Allentown / Bethlehem, PA",
        "https://www.lvashrae.org",
        "squarespace",
        "https://www.lvashrae.org/events",
    ),
    Chapter(
        "125",
        "Roanoke",
        "Roanoke, VA",
        "https://www.ashraeroanoke.org",
        "unreadable",
        "https://www.ashraeroanoke.org/",
        note="The site often returns HTTP 403 to this scraper.",
    ),
    Chapter(
        "134",
        "Anthracite",
        "Scranton / Wilkes-Barre, PA",
        "https://anthraciteashrae.weebly.com",
        "weebly",
        "https://anthraciteashrae.weebly.com/meetings.html",
    ),
)


def default_since(today: date | None = None) -> date:
    """July 1 of the previous ASHRAE society year (society year starts July 1)."""
    today = today or date.today()
    year = today.year if today.month >= 7 else today.year - 1
    return date(year - 1, 7, 1)


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?is)</p>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(raw).replace("\xa0", " ")
    text = re.sub(r"#[\w\-]+\s*\{[^{}]*\}", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{2,}", "\n", text).strip()


def clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", html_to_text(text)).strip(" -")


def clip(text: str, limit: int = 480) -> str:
    text = clean_line(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(".,; ") + "..."


def parse_long_date(text: str) -> date | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%B %d, %Y").date()
    except ValueError:
        return None


def format_clock(token: str) -> str:
    match = re.match(r"(\d{1,2}:\d{2})\s*([AP]M)", token.strip(), re.I)
    if not match:
        return token.strip()
    return f"{match.group(1)} {match.group(2).upper()}"


def time_label(text: str) -> str:
    match = TIME_RE.search(text)
    if not match:
        return ""
    return f"{format_clock(match.group(1))}–{format_clock(match.group(2))}"


def is_yea_event(title: str, body: str, categories: str = "") -> bool:
    """True when this listing is a YEA event, not a speaker bio that mentions YEA."""
    if YEA_RE.search(title) or YOUNG_ENGINEERS_RE.search(title):
        return True
    if YEA_RE.search(categories):
        return True
    theme = re.search(r"Theme:\s*([^\n.]+)", body or "", re.I)
    if theme and YEA_RE.search(theme.group(1)):
        return True
    lead = re.sub(r"https?://\S+", " ", clean_line(body or ""))[:450]
    if re.search(r"Young Engineers (?:in|of) ASHRAE", lead, re.I):
        return True
    if re.search(r"\b(?:open to|join|joins|welcome|welcomes|invites|hosted by)\b.{0,80}\bYEA\b", lead, re.I):
        return True
    if re.search(r"\bYEA\b.{0,40}\b(?:members|social|happy hour|panel|bowling)\b", lead, re.I):
        return True
    return False


def absolute_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base.rstrip("/") + "/", href)


def canonical_link(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    query = urllib.parse.parse_qs(parts.query)
    query.pop("ts", None)
    kept = urllib.parse.urlencode({key: values[0] for key, values in query.items()})
    path = parts.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, kept, ""))


def join_location(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        for piece in re.split(r"\s*,\s*", clean_line(part)):
            if not piece:
                continue
            if piece.lower() in {"united states", "venue website", "directions"}:
                continue
            if re.match(r"https?://", piece, re.I):
                continue
            if any(piece.lower() == item.lower() for item in seen):
                continue
            seen.append(piece)
    return ", ".join(seen)


def with_area(location: str, area: str) -> str:
    """Add the chapter area when the venue line does not already name that city."""
    if not location:
        return area
    city = area.split(",")[0].split("/")[0].strip()
    if city.lower() not in location.lower():
        return join_location(location, area)
    return location


def other_chapters(host: str, title: str, description: str) -> list[str]:
    # Only the title and the opening pitch. Speaker bios name other chapters.
    text = clean_line(f"{title}\n{clean_line(description)[:350]}")
    found = [host]
    for name, patterns in CHAPTER_ALIASES.items():
        if name == host:
            continue
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            found.append(name)
    return found


def short_topic(topic: str) -> str:
    topic = clean_line(topic).replace(" & ", " and ")
    topic = re.sub(r"\s+Concepts\b.*$", "", topic).strip()
    if ":" in topic:
        head, tail = topic.split(":", 1)
        if len(tail.strip()) > 40:
            topic = head.strip()
    if len(topic) > 72:
        topic = topic[:72].rsplit(" ", 1)[0].rstrip(".,;:")
    return topic


def format_theme(raw: str) -> str:
    labels = {"YEA": "YEA", "WIA": "WiA", "DIA": "DiA", "DEA": "DiA", "SA": "Student Activities"}
    pieces = [piece.strip() for piece in re.split(r"[/,]", raw) if piece.strip()]
    pretty = [labels.get(piece.upper(), piece) for piece in pieces]
    if len(pretty) <= 1:
        return pretty[0] if pretty else "YEA"
    return ", ".join(pretty[:-1]) + f", and {pretty[-1]}"


def polish_title(title: str, description: str) -> str:
    """Turn chapter-site titles into a consistent event name."""
    title = clean_line(title).replace(" & ", " and ")
    title = re.sub(r"\bYEA\s+and\s+SA\b", "YEA and Student Activities", title, flags=re.I)
    title = re.sub(r"\bw/\s*", "with ", title, flags=re.I)
    title = re.sub(r"\s*\((?:free event|free)\)", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip()

    if re.search(r"bowling", f"{title} {description}", re.I) and re.search(
        r"student activities|YEA and SA|\bYEA\b", title, re.I
    ):
        if re.search(r"student activities|\bSA\b", f"{title} {description}", re.I):
            return "YEA and Student Activities Bowling Night"

    if re.search(r"soccer", f"{title} {description}", re.I) and re.search(
        r"\b(union|lehigh|philly|philadelphia)\b", f"{title} {description}", re.I
    ):
        return "YEA Philadelphia Union Soccer Game"

    if re.search(r"\borioles\b", title, re.I):
        return "YEA Baltimore Orioles Game"

    if re.search(r"\bPE\b", title) and re.search(r"panel", title, re.I):
        return "YEA PE Exam Panel"

    if re.search(r"cocktail", title, re.I):
        return "YEA Cocktail Class"

    if re.search(r"board room", title, re.I) and re.search(r"brew", description, re.I):
        return "YEA Brewing HVAC Happy Hour"

    theme = re.search(r"Theme:\s*([^\n.]+)", description, re.I)
    topic = re.search(r"Topic:\s*([^\n.]+)", description, re.I)
    if theme and YEA_RE.search(theme.group(1)) and re.search(r"chapter meeting", title, re.I):
        month = ""
        month_match = re.search(rf"({MONTHS})\s+\d{{4}}", title, re.I)
        if month_match:
            month = month_match.group(0)
        topic_text = short_topic(topic.group(1) if topic else "Chapter program")
        prefix = f"{month} Chapter Meeting" if month else "Chapter Meeting"
        if re.search(r"\b(virtual|PES)\b", title, re.I):
            prefix += " (Virtual)"
        return f"{prefix}: {topic_text} ({format_theme(theme.group(1))})"

    if re.search(r"headshot", title, re.I):
        if re.search(r"happy hour", title, re.I):
            return "YEA Headshots and Happy Hour"
        return "YEA Professional Headshots"

    title = re.sub(
        r"^(YEA(?: and Student Activities)?)\s+(.+?)\s+Event$",
        r"\1 \2",
        title,
        flags=re.I,
    )
    if not title.lower().startswith("yea") and YEA_RE.search(title):
        title = YEA_RE.sub("YEA", title, count=1)
    return title


def build_description(time_text: str, body: str, title: str) -> str:
    body = clean_line(body)
    body = re.sub(r"Membership:\s*Select Membership.*$", "", body, flags=re.I).strip()
    body = re.sub(r"\s+(?:\d{4}\s+)?YEA Soccer Game from \$\d+(?:\.\d{2})?", "", body).strip()
    if re.search(r"email colin to reserve your spot", body, re.I) and len(body) < 80:
        body = "Free headshots and happy hour. Email Colin to reserve a spot."
    if body.lower() == "bowling night":
        body = "Bowling night for Young Engineers in ASHRAE and student activities."
    if re.fullmatch(r"YEA Orioles Game", body, re.I):
        body = "YEA night at an Orioles game."
    if re.fullmatch(r"YEA Cocktail Class", body, re.I):
        body = "Cocktail class for Young Engineers in ASHRAE."
    if body.lower() in {title.lower(), "ashrae", "flyer", "yea"}:
        body = ""
    if time_text and body:
        return clip(f"{time_text}. {body}")
    return clip(time_text or body)


def event_tokens(name: str) -> set[str]:
    stop = {
        "yea",
        "and",
        "the",
        "at",
        "of",
        "a",
        "for",
        "with",
        "ashrae",
        "young",
        "engineers",
        "event",
        "social",
    }
    return {word for word in re.findall(r"[a-z0-9]+", name.lower()) if word not in stop and len(word) > 2}


def similar_event(left: Event, right: Event) -> bool:
    if left.when != right.when:
        return False
    left_tokens = event_tokens(left.name)
    right_tokens = event_tokens(right.name)
    if len(left_tokens) < 2 or len(right_tokens) < 2:
        return False
    shared = left_tokens & right_tokens
    if len(shared) < 2:
        return False
    return len(shared) / len(left_tokens | right_tokens) >= 0.5


def merge_pair(left: Event, right: Event) -> Event:
    primary, secondary = (left, right) if len(left.description) >= len(right.description) else (right, left)
    chapters: list[str] = []
    for name in primary.chapters + secondary.chapters:
        if name not in chapters:
            chapters.append(name)
    return Event(
        name=primary.name,
        when=primary.when,
        description=primary.description or secondary.description,
        location=primary.location or secondary.location,
        chapters=chapters,
        flyer=primary.flyer or secondary.flyer,
        link=primary.link or secondary.link,
        time_label=primary.time_label or secondary.time_label,
        source=primary.source,
    )


def merge_duplicates(events: list[Event]) -> list[Event]:
    merged: list[Event] = []
    for event in events:
        for index, existing in enumerate(merged):
            if similar_event(existing, event) or (
                existing.link and canonical_link(existing.link) == canonical_link(event.link)
            ):
                merged[index] = merge_pair(existing, event)
                break
        else:
            merged.append(event)
    return merged


def parse_meeting_lists(page_html: str) -> list[dict[str, str]]:
    """Parse StarChapter meeting cards from a future or archive page."""
    cards: list[dict[str, str]] = []
    for chunk in re.split(r'<div class="meeting-list">', page_html)[1:]:
        title_match = re.search(r"<h3>(.*?)</h3>", chunk, re.S)
        if not title_match:
            continue
        info_match = re.search(r'<div class="info">(.*)<p class="clear">', chunk, re.S)
        info_html = info_match.group(1) if info_match else chunk
        blurb_match = re.search(r'<p class="clear">(.*?)</p>', chunk, re.S)
        link_match = re.search(r'href=["\']([^"\']*meetinginfo\.php\?[^"\']*)["\']', chunk, re.I)
        image_match = re.search(
            r"<img[^>]+src=['\"]([^'\"]*images/meeting/[^'\"]+)['\"]",
            chunk,
            re.I,
        )
        strongs = [
            clean_line(item)
            for item in re.findall(r"<strong>(.*?)</strong>", info_html, re.S)
        ]
        venue = next((item for item in strongs if item and not DATE_RE.search(item)), "")
        info_text = html_to_text(info_html)
        address_lines: list[str] = []
        place_match = re.search(r'<div class="place">(.*?)</div>', info_html, re.S)
        address_html = place_match.group(1) if place_match else info_html
        for line in html_to_text(address_html).split("\n"):
            line = clean_line(line)
            if not line or line == venue or DATE_RE.search(line) or TIME_RE.search(line):
                continue
            if line.lower() in {"venue website", "add to calendar", "directions"}:
                continue
            address_lines.append(line)
        cards.append(
            {
                "title": clean_line(title_match.group(1)),
                "blurb": clean_line(blurb_match.group(1)) if blurb_match else "",
                "info_text": info_text,
                "venue": venue,
                "address": ", ".join(address_lines),
                "link": html.unescape(link_match.group(1)) if link_match else "",
                "image": image_match.group(1) if image_match else "",
            }
        )
    return cards


def meeting_id(link: str) -> str:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
    values = query.get("id") or []
    return values[0] if values else ""


def detail_text(page_html: str) -> tuple[str, str]:
    """Return the event write-up and a flyer image from a StarChapter detail page."""
    match = re.search(
        r'<div class="details[^"]*">(.*?)(?:<div class="meetingActions"|</div>\s*</div>)',
        page_html,
        re.S,
    )
    block = match.group(1) if match else ""
    flyer = ""
    for src in re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", block, re.I):
        if "logo" in src.lower():
            continue
        flyer = src
        break
    return html_to_text(block), flyer


def scrape_starchapter(fetcher: Fetcher, chapter: Chapter, since: date) -> list[Event]:
    years = range(since.year, date.today().year + 2)
    pages = [f"{chapter.website}/meetinginfo.php?p_or_f=f", f"{chapter.website}/meetinginfo.php?p_or_f=p"]
    pages.extend(f"{chapter.website}/meetinginfo.php?p_or_f=p&y={year}" for year in years)
    cards: dict[str, dict[str, str]] = {}
    loaded = 0
    page_errors: list[str] = []
    for url in pages:
        try:
            page = fetcher.get(url)
        except FetchError as exc:
            page_errors.append(str(exc))
            continue
        loaded += 1
        for card in parse_meeting_lists(page):
            key = meeting_id(card["link"]) or f"{card['title']}|{card['info_text'][:40]}"
            cards.setdefault(key, card)
    if loaded == 0 and page_errors:
        raise FetchError(chapter.website, 0, page_errors[0])

    in_window: list[dict[str, str]] = []
    for card in cards.values():
        when = parse_long_date(card["info_text"])
        if when is None or when < since:
            continue
        card["when"] = when.isoformat()
        in_window.append(card)

    # Open detail pages for YEA titles and for socials whose write-up may say YEA.
    social = re.compile(
        r"\b(social|happy hour|game|bowling|tour|mixer|headshot|panel|soccer|cocktail|trivia|bears)\b",
        re.I,
    )
    in_window = [
        card
        for card in in_window
        if is_yea_event(card["title"], card["blurb"]) or social.search(f"{card['title']} {card['blurb']}")
    ]

    def load_detail(card: dict[str, str]) -> tuple[dict[str, str], str, str]:
        link = card["link"]
        if not link:
            return card, "", ""
        try:
            page = fetcher.get(absolute_url(chapter.website, link))
        except FetchError:
            return card, "", ""
        return card, *detail_text(page)

    detailed = [load_detail(card) for card in in_window]

    events: list[Event] = []
    for card, body, detail_flyer in detailed:
        when = date.fromisoformat(card["when"])
        description_source = body or card["blurb"]
        if not is_yea_event(card["title"], description_source):
            continue
        title = polish_title(card["title"], description_source)
        image = detail_flyer or card["image"]
        if image and "logo" in image.lower():
            image = ""
        location = with_area(join_location(card["venue"], card["address"]), chapter.area)
        link = canonical_link(absolute_url(chapter.website, card["link"])) if card["link"] else chapter.events_url
        events.append(
            Event(
                name=title,
                when=when,
                description=build_description(time_label(card["info_text"]), description_source, title),
                location=location,
                chapters=other_chapters(chapter.name, card["title"], description_source),
                flyer=absolute_url(chapter.website, image) if image else "",
                link=link,
                time_label=time_label(card["info_text"]),
                source=chapter.name,
            )
        )
    return events


def squarespace_items(payload: dict) -> list[dict]:
    items: list[dict] = []
    for key in ("upcoming", "past"):
        value = payload.get(key) or []
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def squarespace_when(item: dict) -> datetime | None:
    raw = item.get("startDate")
    if not isinstance(raw, (int, float)):
        return None
    return datetime.fromtimestamp(raw / 1000, EASTERN)


def location_hint(notes_html: str, title: str, when: date) -> str:
    text = html_to_text(notes_html)
    title_words = [word for word in re.findall(r"[A-Za-z0-9&]+", title) if len(word) > 3]
    for match in re.finditer(rf"({MONTHS})\s+\d{{1,2}},\s+\d{{4}}(.{{0,180}})", text, re.I):
        segment = match.group(0)
        segment_date = parse_long_date(segment)
        shares_title = sum(word.lower() in segment.lower() for word in title_words) >= 2
        if segment_date != when and not shares_title:
            continue
        place = re.search(r"\bat\s+(.+?)(?:\.|$)", segment, re.I)
        if place:
            return clean_line(place.group(1))
    return ""


def scrape_squarespace(fetcher: Fetcher, chapter: Chapter, since: date) -> list[Event]:
    import json

    payload = json.loads(fetcher.get(f"{chapter.events_url}?format=json"))
    notes = ""
    if chapter.notes_url:
        try:
            notes = fetcher.get(chapter.notes_url)
        except FetchError:
            notes = ""
    events: list[Event] = []
    for item in squarespace_items(payload):
        moment = squarespace_when(item)
        if moment is None or moment.date() < since:
            continue
        title = clean_line(item.get("title") or "")
        body = html_to_text(item.get("body") or "")
        categories = " ".join(str(tag) for tag in (item.get("tags") or []) + (item.get("categories") or []))
        confirmed = is_yea_event(title, body, categories)
        if not confirmed:
            continue
        hint = location_hint(notes, title, moment.date()) if notes else ""
        location = join_location(
            (item.get("location") or {}).get("addressTitle", "")
            if isinstance(item.get("location"), dict)
            else "",
            (item.get("location") or {}).get("addressLine1", "")
            if isinstance(item.get("location"), dict)
            else "",
            (item.get("location") or {}).get("addressLine2", "")
            if isinstance(item.get("location"), dict)
            else "",
            hint,
        )
        if hint and chapter.area.split(",")[-1].strip() not in location:
            location = join_location(location, chapter.area)
        if not location:
            location = chapter.area
        link = absolute_url(chapter.website, str(item.get("fullUrl") or chapter.events_url))
        asset = str(item.get("assetUrl") or "")
        flyer = asset if re.search(r"\.(png|jpe?g|gif|webp|pdf)(\?|$)", asset, re.I) else ""
        end = item.get("endDate")
        label = ""
        if isinstance(end, (int, float)):
            end_at = datetime.fromtimestamp(end / 1000, EASTERN)
            label = (
                f"{moment.strftime('%I:%M %p').lstrip('0')}–"
                f"{end_at.strftime('%I:%M %p').lstrip('0')}"
            )
        polished = polish_title(title, body)
        events.append(
            Event(
                name=polished,
                when=moment.date(),
                description=build_description(label, body, polished),
                location=location,
                chapters=other_chapters(chapter.name, title, body),
                flyer=flyer,
                link=canonical_link(link),
                time_label=label,
                source=chapter.name,
            )
        )
    return events


def tribe_location(venue: object) -> str:
    if isinstance(venue, list):
        venue = venue[0] if venue else {}
    if not isinstance(venue, dict):
        return ""
    return join_location(
        str(venue.get("venue") or venue.get("name") or ""),
        str(venue.get("address") or ""),
        str(venue.get("city") or ""),
        " ".join(part for part in (str(venue.get("state") or ""), str(venue.get("zip") or "")) if part),
    )


def scrape_tribe(fetcher: Fetcher, chapter: Chapter, since: date) -> list[Event]:
    import json

    events: list[Event] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        url = (
            f"{chapter.events_url}?per_page=50&page={page}"
            f"&start_date={since.isoformat()}&status=publish"
        )
        payload = json.loads(fetcher.get(url))
        total_pages = int(payload.get("total_pages") or 1)
        for item in payload.get("events") or []:
            if not isinstance(item, dict):
                continue
            start = str(item.get("start_date") or "")
            try:
                moment = datetime.strptime(start[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if moment.date() < since:
                continue
            title = clean_line(str(item.get("title") or ""))
            body = html_to_text(str(item.get("description") or ""))
            categories = " ".join(
                str(cat.get("name") or "")
                for cat in (item.get("categories") or [])
                if isinstance(cat, dict)
            )
            if not is_yea_event(title, body, categories):
                continue
            end_raw = str(item.get("end_date") or "")
            label = ""
            try:
                end_at = datetime.strptime(end_raw[:19], "%Y-%m-%d %H:%M:%S")
                label = (
                    f"{moment.strftime('%I:%M %p').lstrip('0')}–"
                    f"{end_at.strftime('%I:%M %p').lstrip('0')}"
                )
            except ValueError:
                label = moment.strftime("%I:%M %p").lstrip("0")
            image = item.get("image") or {}
            flyer = image.get("url") if isinstance(image, dict) else ""
            if flyer and not re.search(r"flyer|poster|yea", flyer, re.I):
                flyer = ""
            polished = polish_title(title, body)
            link = canonical_link(str(item.get("url") or chapter.website))
            location = tribe_location(item.get("venue"))
            if not location and re.search(r"\bvirtual\b", f"{title} {body[:250]}", re.I):
                location = "Virtual"
            events.append(
                Event(
                    name=polished,
                    when=moment.date(),
                    description=build_description(label, body, polished),
                    location=location or chapter.area,
                    chapters=other_chapters(chapter.name, title, body),
                    flyer=str(flyer or ""),
                    link=link,
                    time_label=label,
                    source=chapter.name,
                )
            )
        page += 1
    return events


def scrape_weebly(fetcher: Fetcher, chapter: Chapter, since: date) -> list[Event]:
    home = fetcher.get(chapter.website)
    urls = [chapter.events_url, chapter.website]
    for href in re.findall(r'href=["\']([^"\']+)["\']', home):
        full = absolute_url(chapter.website, href)
        if urllib.parse.urlsplit(full).netloc != urllib.parse.urlsplit(chapter.website).netloc:
            continue
        if re.search(r"event|meeting|yea|calendar", full, re.I) and full not in urls:
            urls.append(full)
        if len(urls) >= 8:
            break
    events: list[Event] = []
    seen: set[tuple[date, str]] = set()
    for url in urls:
        try:
            text = html_to_text(fetcher.get(url))
        except FetchError:
            continue
        for match in YEA_RE.finditer(text):
            window = text[max(0, match.start() - 120) : match.end() + 160]
            when = parse_long_date(window)
            if when is None or when < since:
                continue
            title = polish_title("YEA event", window)
            key = (when, title)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                Event(
                    name=title,
                    when=when,
                    description=build_description("", window, title),
                    location=chapter.area,
                    chapters=[chapter.name],
                    flyer="",
                    link=canonical_link(url),
                    source=chapter.name,
                )
            )
    return events


def scrape_unreadable(fetcher: Fetcher, chapter: Chapter, since: date) -> list[Event]:
    page = fetcher.get(chapter.website)
    lowered = page.lower()
    if "meeting-list" in lowered or "starchapter" in lowered:
        return scrape_starchapter(fetcher, chapter, since)
    if "wp-json/tribe" in lowered or "tribe-events" in lowered:
        return scrape_tribe(fetcher, chapter, since)
    if "squarespace" in lowered:
        return scrape_squarespace(fetcher, chapter, since)
    raise FetchError(chapter.website, 200, chapter.note or "no event feed recognized")


SCRAPERS = {
    "starchapter": scrape_starchapter,
    "squarespace": scrape_squarespace,
    "tribe": scrape_tribe,
    "weebly": scrape_weebly,
    "unreadable": scrape_unreadable,
}


def scrape_chapter(fetcher: Fetcher, chapter: Chapter, since: date) -> ScrapeReport:
    try:
        events = SCRAPERS[chapter.platform](fetcher, chapter, since)
    except FetchError as exc:
        message = chapter.note or str(exc)
        return ScrapeReport(chapter, error=message)
    except Exception as exc:  # keep one bad site from discarding the rest
        return ScrapeReport(chapter, error=str(exc))
    return ScrapeReport(chapter, events=events)


def to_row(event: Event) -> dict[str, str]:
    return {
        "Title": event.name,
        "Date": event.when.isoformat(),
        "Description": event.description,
        "Location": event.location,
        "Chapter(s)": "; ".join(event.chapters),
        "Flyer": event.flyer,
        "External Link": event.link,
    }


def row_matches(existing: dict[str, str], scraped: dict[str, str]) -> bool:
    if existing.get("Date") != scraped.get("Date"):
        return False
    old_link = canonical_link(existing.get("External Link", ""))
    new_link = canonical_link(scraped.get("External Link", ""))
    if old_link and old_link == new_link:
        return True
    left = event_tokens(existing.get("Title", ""))
    right = event_tokens(scraped.get("Title", ""))
    if len(left) < 2 or len(right) < 2:
        return False
    shared = left & right
    return len(shared) >= 2 and len(shared) / len(left | right) >= 0.5


def managed_link(link: str) -> bool:
    host = urllib.parse.urlsplit(link).netloc.lower().removeprefix("www.")
    if not host:
        return False
    if host.endswith(".starchapter.com"):
        return True
    for chapter in CHAPTERS:
        site = urllib.parse.urlsplit(chapter.website).netloc.lower().removeprefix("www.")
        if host == site:
            return True
    return False


def chapter_for_link(link: str) -> Chapter | None:
    host = urllib.parse.urlsplit(link).netloc.lower().removeprefix("www.")
    if not host:
        return None
    for chapter in CHAPTERS:
        site = urllib.parse.urlsplit(chapter.website).netloc.lower().removeprefix("www.")
        if host == site:
            return chapter
        token = site.split(".")[0].replace("-", "")
        if host.endswith(".starchapter.com") and token and token in host.replace("-", ""):
            return chapter
    return None


def merge_csv(
    existing_rows: list[dict[str, str]],
    scraped_rows: list[dict[str, str]],
    since: date,
    refreshed_chapters: set[str],
) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    used = set()
    for old in existing_rows:
        match_at = next(
            (index for index, new in enumerate(scraped_rows) if index not in used and row_matches(old, new)),
            None,
        )
        if match_at is None:
            old_date = old.get("Date") or ""
            in_window = (not old_date) or old_date >= since.isoformat()
            owner = chapter_for_link(old.get("External Link", ""))
            if (
                in_window
                and owner is not None
                and owner.name in refreshed_chapters
                and managed_link(old.get("External Link", ""))
            ):
                continue
            kept.append({field_name: old.get(field_name, "") for field_name in CSV_FIELDS})
            continue
        used.add(match_at)
        kept.append(scraped_rows[match_at])
    kept.extend(row for index, row in enumerate(scraped_rows) if index not in used)
    kept.sort(key=lambda row: (row.get("Date") or "9999", row.get("Title") or ""))
    return kept


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = []
        for row in csv.DictReader(handle):
            if not (row.get("Title") or row.get("Name")):
                continue
            normalized = {field_name: row.get(field_name, "") or "" for field_name in CSV_FIELDS}
            if not normalized["Title"]:
                normalized["Title"] = row.get("Name", "") or ""
            rows.append(normalized)
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape YEA events from Region III chapter websites.")
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        default=None,
        help="Include events on or after this date (YYYY-MM-DD). Default: July 1 of the previous society year.",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Events CSV to update.")
    parser.add_argument(
        "--chapters",
        default="",
        help="Comma-separated chapter names or numbers to scrape. Other chapters are left unchanged.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print events without writing the CSV.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    since = args.since or default_since()
    fetcher = Fetcher()
    selected = CHAPTERS
    if args.chapters.strip():
        wanted = {part.strip().lower() for part in args.chapters.split(",") if part.strip()}
        selected = tuple(
            chapter
            for chapter in CHAPTERS
            if chapter.name.lower() in wanted or chapter.number in wanted
        )
        if not selected:
            print("No matching chapters. Known chapters:")
            for chapter in CHAPTERS:
                print(f"  {chapter.number} {chapter.name}")
            return 1
    reports: list[ScrapeReport] = []
    for chapter in selected:
        print(f"Fetching {chapter.name}...", flush=True)
        reports.append(scrape_chapter(fetcher, chapter, since))

    events = merge_duplicates([event for report in reports for event in report.events])
    scraped_rows = [to_row(event) for event in events]
    existing = read_csv(args.csv)
    refreshed = {report.chapter.name for report in reports if not report.error}
    merged = merge_csv(existing, scraped_rows, since, refreshed)
    added = max(0, len(merged) - len(existing))

    print(f"\nYEA events on or after {since.isoformat()}:")
    if not scraped_rows:
        print("  (none found)")
    for row in sorted(scraped_rows, key=lambda item: (item["Date"], item["Title"])):
        print(f"  {row['Date']}  {row['Title']}  [{row['Chapter(s)']}]")

    print("\nChapter results:")
    for report in reports:
        if report.error:
            print(f"  {report.chapter.name}: not scraped - {report.error}")
        else:
            print(f"  {report.chapter.name}: {len(report.events)} YEA event(s)")

    if args.dry_run:
        print(f"\nDry run. {len(scraped_rows)} scraped event(s); CSV not written.")
        return 0
    write_csv(args.csv, merged)
    print(f"\nWrote {len(merged)} row(s) to {args.csv} ({len(scraped_rows)} scraped, {added} new).")
    failures = [report for report in reports if report.error]
    return 1 if failures and not scraped_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
