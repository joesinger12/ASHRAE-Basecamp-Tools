# ASHRAE Basecamp Tools

Small Python package and CLI for ASHRAE committee work on Basecamp. It wraps the official [`basecamp-sdk`](https://pypi.org/project/basecamp-sdk/) instead of reimplementing the API.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Auth

Basecamp’s API does **not** accept a username and password (no Basic auth). You still sign in with your Basecamp email/password, but only on Basecamp’s own website during OAuth. This tool never sees your password.

### Get a token (official CLI)

```bash
# https://github.com/basecamp/basecamp-cli
basecamp auth login
basecamp auth token
```

`auth login` opens a browser. Sign in there, then copy the token into `.env`:

```
BASECAMP_TOKEN=...
BASECAMP_ACCOUNT_ID=3106353
```

Or run `ashrae-bc login`, which uses device flow when Basecamp advertises it, otherwise the official `basecamp` CLI if it is installed.

Then:

```bash
ashrae-bc whoami
```

Tokens last about two weeks. The CLI also reads `BASECAMP_TOKEN` / `BASECAMP_ACCOUNT_ID` from the environment if they are already set.

## CLI

```bash
ashrae-bc login
ashrae-bc whoami
ashrae-bc get https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc get 10269026711 --format text
ashrae-bc links https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc brief https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc append https://3.basecamp.com/3106353/buckets/352581/documents/10269026711 --text "A short note"
ashrae-bc search "agenda" --type Document --project 352581
```

`put` replaces the document body. Always prefer `append` when adding a line. Updates send both `title` and `content` so Basecamp does not clear omitted fields.

## Cursor skill

This repo includes `.cursor/skills/email-prep/`. Ask the agent to prep/draft an email (or name `email-prep`); it will call `ashrae-bc` and return a paste-ready plain-text body with Basecamp links. It does not send mail.
