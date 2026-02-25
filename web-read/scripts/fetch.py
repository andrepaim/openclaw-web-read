#!/usr/bin/env python3
"""
fetch.py — Three-tier web content fetcher

Tier 1: HTTP + BeautifulSoup   — fast, works for static pages
Tier 2: Jina AI Reader         — JS-rendered SPAs, free, no API key
Tier 3: Local Playwright       — Cloudflare-protected and stubborn pages

Usage:
    python3 fetch.py <url> [timeout_seconds]

Output: clean text/markdown to stdout
Exit:   0 on success, 1 on failure
"""

import sys
import re


# ─── Quality check ────────────────────────────────────────────────────────────

BLOCK_SIGNALS = [
    "just a moment",
    "enable javascript",
    "checking your browser",
    "please wait",
    "ddos protection",
    "access denied",
    "403 forbidden",
    "404 not found",
]

def is_useful(text: str) -> bool:
    if not text or len(text.strip()) < 350:
        return False
    head = text.lower()[:600]
    return not any(sig in head for sig in BLOCK_SIGNALS)


# ─── Output cleaning ──────────────────────────────────────────────────────────

def clean(text: str) -> str:
    lines = text.split("\n")
    out, prev_blank = [], False
    for line in lines:
        stripped = line.rstrip()
        blank = not stripped
        if blank and prev_blank:
            continue
        out.append(stripped)
        prev_blank = blank
    return "\n".join(out).strip()


# ─── Tier 1: plain HTTP ───────────────────────────────────────────────────────

def tier1_http(url: str, timeout: int) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.body
        )
        body_text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

        return f"# {title}\n\n{body_text}" if title else body_text

    except ImportError:
        return ""  # requests/bs4 not installed — fall through
    except Exception:
        return ""


# ─── Tier 2: Jina AI Reader ───────────────────────────────────────────────────

def tier2_jina(url: str, timeout: int) -> str:
    """
    Free cloud service — no API key needed.
    Prepends https://r.jina.ai/ to the target URL; Jina renders the page
    with headless Chrome and returns clean markdown.
    """
    try:
        import requests

        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "X-Timeout": str(min(timeout, 30)),
            "Accept": "text/plain, text/markdown",
        }
        r = requests.get(jina_url, headers=headers, timeout=timeout + 10)
        return r.text
    except ImportError:
        return ""
    except Exception:
        return ""


# ─── Tier 3: local Playwright ─────────────────────────────────────────────────

def tier3_playwright(url: str, timeout: int) -> str:
    """
    Requires: pip install playwright && playwright install chromium
    Used as last resort for pages that Jina can't render (heavy Cloudflare, etc.)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.stderr.write(
            "[web-read] Playwright not installed — skipping Tier 3.\n"
            "  Install: pip install playwright && playwright install chromium\n"
        )
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(1500)

            content = page.evaluate("""() => {
                ["script","style","nav","footer","iframe","noscript"]
                    .forEach(t => document.querySelectorAll(t).forEach(e => e.remove()));
                const title = document.title || "";
                const main =
                    document.querySelector("main") ||
                    document.querySelector("article") ||
                    document.querySelector('[role="main"]') ||
                    document.body;
                const text = main ? main.innerText : document.body.innerText;
                return title ? `# ${title}\\n\\n${text}` : text;
            }""")

            browser.close()
            return content

    except Exception as e:
        sys.stderr.write(f"[web-read] Playwright error: {e}\n")
        return ""


# ─── Pipeline ─────────────────────────────────────────────────────────────────

TIERS = [
    ("HTTP",       tier1_http),
    ("Jina",       tier2_jina),
    ("Playwright", tier3_playwright),
]

def fetch(url: str, timeout: int = 20) -> tuple[str, str]:
    """
    Returns (content, tier_name) for the first tier that produces useful content.
    Returns ("", "") if all tiers fail.
    """
    for name, fn in TIERS:
        result = fn(url, timeout)
        if is_useful(result):
            return clean(result), name
    return "", ""


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch.py <url> [timeout_seconds]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    content, tier = fetch(url, timeout)

    if content:
        sys.stderr.write(f"[web-read] Fetched via {tier}\n")
        print(content)
        sys.exit(0)
    else:
        sys.stderr.write("[web-read] All tiers failed — no useful content extracted.\n")
        sys.exit(1)
