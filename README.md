# ASHRAE Basecamp Tools

Small Python package and CLI for ASHRAE committee work on Basecamp. It wraps the official [`basecamp-sdk`](https://pypi.org/project/basecamp-sdk/) instead of reimplementing the API.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Auth

Basecamp uses OAuth access tokens (they expire about every two weeks). There is no API key.

1. Copy `.env.example` to `.env`
2. Put a token in `BASECAMP_TOKEN`
3. Keep `BASECAMP_ACCOUNT_ID=3106353` unless you need another account

Ways to mint a token:

- Official [Basecamp CLI](https://github.com/basecamp/basecamp-cli) login, then copy the access token
- Register an integration at [Launchpad](https://launchpad.37signals.com/integrations) and complete the OAuth flow

The CLI also reads `BASECAMP_TOKEN` / `BASECAMP_ACCOUNT_ID` from the environment if they are already set.

## CLI

```bash
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
