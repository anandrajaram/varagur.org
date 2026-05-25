#!/usr/bin/env python3
"""
Extract the prose content from each cached Squarespace HTML page.

Squarespace puts text-block prose inside <div class="sqs-html-content">...</div>.
We capture all such blocks (handling nested divs by walking char-by-char), drop
empties, and also record every Squarespace CDN image URL referenced anywhere on
the page (so gallery pages keep all their images).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_HTML = REPO_ROOT / "scripts" / "cache" / "html"
OUT_PATH = REPO_ROOT / "scripts" / "cache" / "content.json"

OPEN_DIV = re.compile(r"<div\b[^>]*>", re.IGNORECASE)
CLOSE_DIV = re.compile(r"</div\s*>", re.IGNORECASE)


def extract_balanced_div(html: str, start_idx: int) -> tuple[str, int]:
    """
    Given an index pointing at the '<' of an opening <div ...>, return the
    inner HTML up to the matching </div> and the index just past that </div>.
    """
    # First, find end of the opening tag
    end_open = html.find(">", start_idx)
    if end_open == -1:
        return "", len(html)
    inner_start = end_open + 1
    depth = 1
    pos = inner_start
    while depth > 0:
        m_open = OPEN_DIV.search(html, pos)
        m_close = CLOSE_DIV.search(html, pos)
        if not m_close:
            return html[inner_start:], len(html)
        if m_open and m_open.start() < m_close.start():
            depth += 1
            pos = m_open.end()
        else:
            depth -= 1
            if depth == 0:
                return html[inner_start:m_close.start()], m_close.end()
            pos = m_close.end()
    return "", pos


def extract_sqs_blocks(html: str) -> list[str]:
    """Return inner HTML of every <div class="sqs-html-content">...</div>."""
    blocks: list[str] = []
    for m in re.finditer(r'<div\b[^>]*class="[^"]*sqs-html-content[^"]*"[^>]*>',
                         html, re.IGNORECASE):
        inner, _ = extract_balanced_div(html, m.start())
        text = inner.strip()
        # Filter out empties and obvious noise
        if not text:
            continue
        if len(re.sub(r"<[^>]+>|&[a-z]+;|\s", "", text)) < 3:
            # block contained no real text content (just markup/whitespace)
            continue
        blocks.append(text)
    return blocks


def extract_title(html: str) -> str | None:
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if not m:
        return None
    t = m.group(1)
    t = t.replace("&mdash;", "—").replace("&amp;", "&")
    # Squarespace appends " — Varagur.org" or " - Varagur.org"
    t = re.split(r"\s+[—-]\s+Varagur\.org", t, maxsplit=1)[0]
    return t.strip() or None


def extract_images(html: str) -> list[str]:
    """All Squarespace CDN image URLs referenced on the page (no favicon)."""
    seen: list[str] = []
    for m in re.finditer(
        r'(?:src|data-src|data-image)="(https://images\.squarespace-cdn\.com/[^"?]+)',
        html,
    ):
        u = m.group(1)
        if "favicon" in u:
            continue
        if u not in seen:
            seen.append(u)
    return seen


def main():
    out: dict[str, dict] = {}
    for html_path in sorted(CACHE_HTML.glob("*.html")):
        slug = html_path.stem
        html = html_path.read_text(encoding="utf-8", errors="replace")
        # Restrict to the main-content area when present, otherwise whole page.
        m_main = re.search(r'<div\b[^>]*class="[^"]*main-content[^"]*"[^>]*>',
                           html, re.IGNORECASE)
        if m_main:
            main_html, _ = extract_balanced_div(html, m_main.start())
        else:
            main_html = html
        blocks = extract_sqs_blocks(main_html)
        # Fallback for Squarespace Event Pages and similar templates where
        # the prose lives outside main-content (e.g. page-body-footer).
        if not blocks:
            blocks = extract_sqs_blocks(html)
        # Drop the trailing newsletter / signup blocks that look like Squarespace
        # widgets common to every page footer.
        blocks = [b for b in blocks if not re.search(
            r"join our mailing list|Get notified about key events|"
            r"Signup to join our mailing list|"
            r"All rights reserved|"
            r"GET NOTIFIED",
            b, re.IGNORECASE)]
        title = extract_title(html)
        # Images: scan the whole page so we catch Squarespace gallery widgets
        # that sit outside the main-content div.
        images = extract_images(html)
        out[slug] = {"title": title, "html_chunks": blocks, "images": images}
        print(f"{slug}: title={title!r}, chunks={len(blocks)}, images={len(images)}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    main()
