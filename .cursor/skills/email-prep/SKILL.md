---
name: email-prep
description: Drafts paste-ready plain-text email bodies for ASHRAE committee work, looking up Basecamp documents and inserting titled Basecamp links. Use when the user asks to prep, draft, or write an email from Basecamp, names email-prep, or wants an email body with Basecamp URLs.
---

# email-prep

Prepare a paste-ready **plain-text** email body. Do not send mail.

Use `ashrae-bc` from this repo. Do not call the Basecamp HTTP API directly.

## Steps

1. Split the request into facts the user already gave vs items to look up (URLs, titles, search terms).
2. Look up Basecamp sources:
   - Document URL or id: `ashrae-bc get <url-or-id> --format json` and `ashrae-bc brief <url-or-id>`
   - Links in a page: `ashrae-bc links <url-or-id>`
   - Search: `ashrae-bc search "query" --type Document` (add `--project 352581` when scoped to the usual ASHRAE project)
3. Draft the body from the requested information. Greeting is optional unless the user asked for one.
4. Include Basecamp `app_url` links where requested or where a source was used. Format titled links as `Title: url` on their own line, or inline as `Title (url)`.
5. Print the draft for the user. Do not send it.

## Commands

```bash
ashrae-bc whoami
ashrae-bc get <url-or-id> --format json
ashrae-bc get <url-or-id> --format text
ashrae-bc brief <url-or-id>
ashrae-bc links <url-or-id>
ashrae-bc search "query" --type Document --project 352581
```

Default account is `3106353`. Requires `BASECAMP_TOKEN`.

## Output

Plain text only. Typical shape:

```
[optional greeting]

[requested facts]

[short context pulled from Basecamp]

Links:
Page title: https://3.basecamp.com/...
```
