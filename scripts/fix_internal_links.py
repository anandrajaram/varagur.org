#!/usr/bin/env python3
"""
Rewrite absolute-path internal links in .md content to use Liquid's
`{{ '/path/' | relative_url }}` filter, so they pick up site.baseurl.

This makes the same source work for:
  - the preview deploy (baseurl=/varagur.org)
  - production (baseurl="")
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# href="/path/..." inside HTML blocks
HTML_HREF = re.compile(r'href="(/[a-zA-Z0-9_./-]+)"')

# [text](/path/...) markdown links
MD_LINK = re.compile(r"\]\((/[a-zA-Z0-9_./-]+)\)")


def rewrite(text: str) -> tuple[str, int]:
    n = 0

    def html_sub(m):
        nonlocal n
        n += 1
        return f'href="{{{{ \'{m.group(1)}\' | relative_url }}}}"'

    def md_sub(m):
        nonlocal n
        n += 1
        return f"]({{{{ '{m.group(1)}' | relative_url }}}})"

    text = HTML_HREF.sub(html_sub, text)
    text = MD_LINK.sub(md_sub, text)
    return text, n


def main():
    skip = {"_site", "_layouts", "_includes", "scripts", "assets"}
    total = 0
    files = 0
    for md in REPO.rglob("*.md"):
        if any(part in skip for part in md.parts):
            continue
        original = md.read_text(encoding="utf-8")
        new, n = rewrite(original)
        if n:
            md.write_text(new, encoding="utf-8")
            print(f"  {md.relative_to(REPO)}: {n} link(s) rewritten")
            total += n
            files += 1
    print(f"\n{total} links rewritten across {files} files")


if __name__ == "__main__":
    main()
