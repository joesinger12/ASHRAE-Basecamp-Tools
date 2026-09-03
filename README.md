# ASHRAE Basecamp Tools

Thin ASHRAE helpers on top of the **official Basecamp CLI**. This repo does not reimplement login, search, or document get/update — use `basecamp` for those.

This package only adds workflows the official CLI does not:

- `ashrae-bc append` — add a line to a document without replacing the rest
- `ashrae-bc links` — list URLs in a document
- `ashrae-bc brief` — title, URL, excerpt, and links for email
- `.cursor/skills/email-prep/` — draft a paste-ready email body with Basecamp links

**Install and sign in:** see [docs/SETUP.md](docs/SETUP.md) (CLI, login, Cursor MCP).

```bash
ashrae-bc doctor
ashrae-bc brief https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc append https://3.basecamp.com/3106353/buckets/352581/documents/10269026711 --text "A short note"
```
