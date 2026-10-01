---
name: ashrae-yea-events
description: >-
  Scrapes Young Engineers in ASHRAE (YEA) events from Region III chapter
  websites and merges them into data/events/events.csv. Use when the user asks
  to scrape, refresh, or add chapter YEA events, update events.csv, or pull
  events from Philadelphia, Central Pennsylvania, Pittsburgh, Baltimore,
  National Capital, Hampton Roads, Richmond, Lehigh Valley, Roanoke, or
  Anthracite ASHRAE sites.
---

# ASHRAE chapter YEA events

Run the scraper. Do not hand-copy events into the CSV when the script can read the site.

```bash
python -u scripts/scrape_yea_events.py
```

From the repo root. Requires Python 3.11+ and `curl` on PATH. No third-party packages.

## What it keeps

Events on or after July 1 of the previous ASHRAE society year (society year starts July 1). Override with `--since YYYY-MM-DD`.

An event is YEA when the title, category, or opening description says so, or the listing's theme line includes YEA. A speaker bio that mentions YEA, or names another chapter, does not make it a YEA or joint-chapter event.

Titles are rewritten into a consistent name (for example `YEA PE Exam Panel`, `YEA and Student Activities Bowling Night`). The script refreshes those titles on the next run.

## CSV

`data/events/events.csv`

`Chapter(s),Title,Date,Description,Location,Flyer,External Link`

`Date` is `YYYY-MM-DD`. Joint events list chapters separated by `; `.

Rows from a chapter that was scraped successfully are replaced by the new result. Rows from a chapter that failed this run are left in place. Rows that do not link to a chapter site are left in place.

## Chapters

| Chapter | Site | How events are read |
| --- | --- | --- |
| Philadelphia | https://ashraephilly.org | StarChapter meeting list |
| Central Pennsylvania | https://centralpaashrae.com | StarChapter meeting list |
| Pittsburgh | https://ashraepittsburgh.org/calendar | Squarespace JSON |
| Baltimore | https://ashrae-balto.org | StarChapter meeting list |
| National Capital | https://nccashrae.org | The Events Calendar JSON |
| Hampton Roads | https://ashraehrc.org | No working site (TLS fails). Skip. |
| Richmond | https://richmondashrae.org | The Events Calendar JSON |
| Lehigh Valley | https://www.lvashrae.org/events | Squarespace JSON |
| Roanoke | https://www.ashraeroanoke.org | Often HTTP 403. Record the failure and continue. |
| Anthracite | https://anthraciteashrae.weebly.com/meetings.html | Weebly HTML |

Newsletter PDFs are not parsed.

## Useful flags

- `--dry-run` prints events and does not write the CSV.
- `--chapters "Baltimore,Philadelphia"` scrapes only those chapters.
- `--since 2026-07-01` changes the window.

If StarChapter returns HTTP 429, wait and rerun with `--chapters` for the chapters that failed. Do not delete their existing CSV rows.
