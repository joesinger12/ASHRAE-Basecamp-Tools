# ASHRAE-Basecamp-Tools

## YEA events

`scripts/scrape_yea_events.py` reads Region III chapter sites and merges Young Engineers in ASHRAE (YEA) events into `data/events/events.csv`.

```bash
python -u scripts/scrape_yea_events.py
```

Requires Python 3.11+ and curl. Hampton Roads has no working website. See `.cursor/skills/ashrae-yea-events/SKILL.md` for the chapter list and flags.