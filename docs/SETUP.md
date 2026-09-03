# Install and use Basecamp for ASHRAE

Use the **official Basecamp CLI** as the API client. This repo only adds append / links / brief / email-prep on top of it.

Username and password cannot be sent to the Basecamp API. You sign in with your Basecamp account in a **browser** during `basecamp auth login`. The CLI stores the OAuth token and refreshes it.

## 1. Install the official Basecamp CLI

macOS, Linux, or WSL:

```bash
curl -fsSL https://basecamp.com/install-cli | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/basecamp/basecamp-cli/main/scripts/install.ps1 | iex
```

Other methods (Homebrew, Scoop, apt): [basecamp-cli README](https://github.com/basecamp/basecamp-cli).

Check:

```bash
basecamp --version
```

## 2. Sign in

```bash
basecamp auth login
```

A browser opens. Sign in to Basecamp and approve access.

Confirm:

```bash
basecamp auth status
```

To print a token for scripts (usually unnecessary — the CLI already stores it):

```bash
basecamp auth token
```

Tokens last about two weeks; the official CLI refreshes them.

## 3. Use this repo’s project defaults

This repo includes `.basecamp/config.json` with:

- account `3106353`
- project `352581` (the project that holds the test AI page)

After cloning, trust that config once:

```bash
basecamp config trust
```

## 4. Install the ASHRAE helpers (optional, for append / links / brief)

```bash
cd ASHRAE-Basecamp-Tools
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ashrae-bc doctor
```

## 5. Everyday commands

**Official CLI** (generic Basecamp work):

```bash
basecamp auth status
basecamp url parse "https://3.basecamp.com/3106353/buckets/352581/documents/10269026711" --json
basecamp files show 10269026711 --in 352581 --json
basecamp files update 10269026711 --title "New title" --in 352581
basecamp search "agenda" --type document --json
```

**This repo** (ASHRAE-only helpers):

```bash
ashrae-bc brief https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc links https://3.basecamp.com/3106353/buckets/352581/documents/10269026711
ashrae-bc append https://3.basecamp.com/3106353/buckets/352581/documents/10269026711 --text "A short note"
```

`append` only adds a fragment. Do not use `basecamp files update --content` unless you intend to replace the whole body.

## 6. Cursor MCP (recommended)

The official CLI can serve Basecamp as MCP tools (`basecamp_projects`, `basecamp_todos`, `basecamp_files`, search, and more). This repo already has [`.cursor/mcp.json`](../.cursor/mcp.json):

```json
{
  "mcpServers": {
    "basecamp": {
      "type": "stdio",
      "command": "basecamp",
      "args": ["mcp"]
    }
  }
}
```

1. Finish steps 1–2 so `basecamp` is on your PATH and you are signed in.
2. Restart Cursor or reload the window.
3. Open **Cursor Settings → MCP** and confirm `basecamp` is connected.

Read-only MCP (no writes):

```json
"args": ["mcp", "--read-only"]
```

Limit domains:

```json
"args": ["mcp", "--domains", "projects,files,reports"]
```

User-level config (all projects) is `~/.cursor/mcp.json` with the same `mcpServers` block.

Claude Code can register the same server with:

```bash
claude mcp add basecamp -- basecamp mcp
```

The CLI can also wire agent plugins:

```bash
basecamp setup
```

## 7. email-prep skill

This repo’s `.cursor/skills/email-prep/` drafts paste-ready email bodies. It uses `basecamp` to look up pages and `ashrae-bc brief` / `ashrae-bc links` when you want excerpts and URL lists. It does not send mail.

## What to use when

| Task | Tool |
|---|---|
| Login, token refresh | `basecamp auth login` |
| Read/update a document, search, URL parse | `basecamp …` |
| Agent tools in Cursor | `basecamp mcp` (this repo’s `.cursor/mcp.json`) |
| Append a line, list links, email brief | `ashrae-bc` |
| Draft an email with Basecamp links | `email-prep` skill |
