---
name: email-prep
description: Drafts paste-ready plain-text email bodies for ASHRAE committee work, looking up Basecamp documents and inserting titled Basecamp links. Use when the user asks to prep, draft, or write an email from Basecamp, names email-prep, or wants an email body with Basecamp URLs.
---

# email-prep

Prepare a paste-ready **plain-text** email body. Do not send mail.

Use the official `basecamp` CLI for lookup. Use `ashrae-bc` only for link lists and briefs. Do not call the Basecamp HTTP API directly.

## Steps

1. Split the request into facts the user already gave vs items to look up (URLs, titles, search terms).
2. Look up Basecamp sources:
   - Parse a URL: `basecamp url parse "<url>" --json`
   - Show a document: `basecamp files show <id> --in 352581 --json` (or pass the URL if the command accepts it)
   - Excerpt and links: `ashrae-bc brief <url-or-id>` and `ashrae-bc links <url-or-id>`
   - Search: `basecamp search "query" --type document --json`
3. Draft the body from the requested information. Greeting is optional unless the user asked for one.
4. Include Basecamp `app_url` links where requested or where a source was used. Format titled links as `Title: url` on their own line, or inline as `Title (url)`.
5. Print the draft for the user. Do not send it.

Requires `basecamp auth login` (see docs/SETUP.md). Default project is `352581`.

## Output

Plain text only. Typical shape:

```
[optional greeting]

[requested facts]

[short context pulled from Basecamp]

Links:
Page title: https://3.basecamp.com/...
```
