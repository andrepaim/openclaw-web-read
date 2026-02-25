# web-read — OpenClaw Skill

An [OpenClaw](https://openclaw.ai) skill that fetches readable content from **any URL**, including JavaScript-rendered SPAs and pages that the built-in `web_fetch` tool cannot handle.

## The problem

`web_fetch` works well for static pages but returns an empty shell for most modern web apps — React/Vue SPAs, documentation portals, product pages, SaaS dashboards. The agent sees a blank response and has no fallback.

## How it works

A single Python script (`scripts/fetch.py`) tries three methods in order, returning the first result with meaningful content:

| Tier | Method | Handles |
|---|---|---|
| 1 | HTTP + BeautifulSoup | Static HTML, blogs, plain docs |
| 2 | [Jina AI Reader](https://jina.ai/reader) | JS-rendered SPAs — free, no API key |
| 3 | Local Playwright + Chromium | Cloudflare-protected pages |

Each tier is attempted only if the previous one returns insufficient content (< 350 chars, or contains known block signals like "Just a moment" / "Enable JavaScript"). The script reports which tier succeeded.

Playwright (Tier 3) is **optional** — Tiers 1–2 cover the vast majority of pages with no local browser required.

## Installation

**Install the skill** into your OpenClaw workspace:

```bash
# Clone or copy the web-read/ directory into your skills folder
cp -r web-read/ ~/.openclaw/workspace/skills/

# Install Python dependencies
pip install requests beautifulsoup4

# Optional: install Playwright for Tier 3 (Cloudflare-heavy pages)
pip install playwright && playwright install chromium
```

**Install as a packaged skill** (if you have the `.skill` file):

```bash
openclaw skills install web-read.skill
```

## Usage

The skill is invoked automatically by OpenClaw when the agent reads a URL that `web_fetch` can't handle. You can also run the script directly:

```bash
python3 scripts/fetch.py "https://example.com" [timeout_seconds]
```

Default timeout: 20 seconds. Output is clean markdown/text on stdout. Tier used is reported on stderr.

### Examples

```bash
# Read a JS-rendered documentation page
python3 scripts/fetch.py "https://docs.someproduct.com/quickstart"

# Read a Cloudflare-protected page with extended timeout
python3 scripts/fetch.py "https://protected-site.com/page" 30

# Pipe into another tool
python3 scripts/fetch.py "https://example.com" | llm summarize
```

## Limitations

- **Turnstile / hCaptcha**: Interactive CAPTCHA challenges cannot be solved automatically. If Tier 3 fails, the page requires manual access.
- **Login-gated pages**: Authenticated content requires session cookies — not supported.
- **Rate limits**: Jina AI Reader's free tier has generous but finite limits. For bulk fetching, consider self-hosting Jina or using a paid scraping API.

## Jina Search (bonus)

When `web_search` is rate-limited, Jina also provides a free search endpoint that returns full page content (not just snippets):

```bash
curl "https://s.jina.ai/?q=your+search+query"
```

No API key required.

## File structure

```
web-read/
├── SKILL.md              # OpenClaw skill definition (thin — just invokes the script)
└── scripts/
    └── fetch.py          # Three-tier fetcher (the actual logic)
```

## Requirements

- Python 3.9+
- `requests` and `beautifulsoup4` (Tiers 1–2)
- `playwright` + Chromium (Tier 3, optional)

## License

MIT
