---
name: web-read
description: "Fetch readable content from any URL including JavaScript-rendered SPAs, modern web apps, and pages that web_fetch cannot handle (returns empty, a JS shell, or a Cloudflare block). Use whenever web_fetch fails or returns less than a paragraph of content, or proactively for URLs from known JS-heavy platforms. Handles everything automatically through a 3-tier pipeline — one call, no manual tier selection."
---

# web-read

Run the bundled script:

```bash
python3 <skill_dir>/scripts/fetch.py "<URL>" [timeout_seconds]
```

`<skill_dir>` is the absolute path to this skill's directory (e.g. `~/.openclaw/workspace/skills/web-read`).

Default timeout: 20s. Increase to 30 for slow SPAs.

The script tries three methods internally (HTTP → Jina AI Reader → Playwright) and returns the first result with useful content. Reports which tier succeeded on stderr.

## Dependencies

Install once:

```bash
pip install requests beautifulsoup4 playwright
playwright install chromium   # only needed for Tier 3
```

`requests` and `beautifulsoup4` cover Tiers 1–2. Playwright is optional — if not installed, the script uses the first two tiers only, which handles ~95% of pages.

## When it still fails

Heavy Cloudflare bot challenges (Turnstile/hCaptcha) block all automated approaches. If Tier 3 fails, ask the user to paste the content manually.
