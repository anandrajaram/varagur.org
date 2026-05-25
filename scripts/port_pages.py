#!/usr/bin/env python3
"""
Generate Jekyll markdown files from cached Squarespace content.

Inputs:  scripts/cache/content.json   (from extract_content.py)
         scripts/cache/image_manifest.json  (from download_site.py)

Output:  Page markdown files at the correct permalinks.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT = json.loads((REPO_ROOT / "scripts" / "cache" / "content.json").read_text())
MANIFEST = json.loads((REPO_ROOT / "scripts" / "cache" / "image_manifest.json").read_text())


# slug -> (output_path, permalink, layout, page_title)
PAGE_MAP = {
    # Skip "index" — handcrafted index.md is already written.
    "home__about": ("home/about.md", "/home/about/", "page", "Sthala Puranam"),
    "home__sri-venkatesa-perumal-kovil": ("home/sri-venkatesa-perumal-kovil.md", "/home/sri-venkatesa-perumal-kovil/", "page", "Sri Venkatesa Perumal Kovil"),
    "home__sri-narayana-theerthar": ("home/sri-narayana-theerthar.md", "/home/sri-narayana-theerthar/", "page", "Sri Narayana Theerthar"),
    "utsavams": ("utsavams.md", "/utsavams/", "page", "Utsavams"),
    "overview": ("overview.md", "/overview/", "page", "About Uriyadi"),
    "uriyadi": ("uriyadi.md", "/uriyadi/", "page", "About Uriyadi"),
    "about": ("about.md", "/about/", "page", "About"),
    # Hand-tuned with a real map embed — port_pages.py skips it.
    # "about__where-is-varagur": ("about/where-is-varagur.md", "/about/where-is-varagur/", "page", "Where is Varagur?"),
    "about__varagur-thanjavur-bus-timings": ("about/varagur-thanjavur-bus-timings.md", "/about/varagur-thanjavur-bus-timings/", "page", "Varagur Thanjavur Bus Timings"),
    "about__contact": ("about/contact.md", "/about/contact/", "page", "Contact Us"),
    "about__thank-you": ("about/thank-you.md", "/about/thank-you/", "page", "Thank you"),
    "media": ("media.md", "/media/", "page", "News"),
    "media__videos": ("media/videos.md", "/media/videos/", "page", "Videos"),
    # Gallery pages — use gallery layout
    "uriyadi-2017": ("uriyadi-2017.md", "/uriyadi-2017/", "gallery", "Uriyadi 2017"),
    "uriyadi-2016": ("uriyadi-2016.md", "/uriyadi-2016/", "gallery", "Uriyadi 2016"),
    "uriyadi-2015": ("uriyadi-2015.md", "/uriyadi-2015/", "gallery", "Uriyadi 2015"),
    "uriyadi__uriyadi-2014": ("uriyadi/uriyadi-2014.md", "/uriyadi/uriyadi-2014/", "gallery", "Uriyadi 2014"),
    "uriyadi__uriyadi-2013": ("uriyadi/uriyadi-2013.md", "/uriyadi/uriyadi-2013/", "gallery", "Uriyadi 2013"),
    "uriyadi__uriyadi-2007": ("uriyadi/uriyadi-2007.md", "/uriyadi/uriyadi-2007/", "page", "Uriyadi 2007"),
    # Blog index — hand-tuned to render a post list, so port_pages.py skips it.
    # "blog": ("blog.md", "/blog/", "page", "Blog"),
    # blog post is special — written separately below
}


def html_to_markdown(snippet: str) -> str:
    """Light HTML -> markdown conversion for the Squarespace prose blocks."""
    s = snippet
    # Normalize whitespace entities
    s = s.replace("​", "").replace("\xa0", " ").replace("&nbsp;", " ").replace("&#8203;", "")
    # Strip the heading tags we *don't* want to render as markdown headings on
    # gallery pages where we already have a page-title from front matter.
    # We'll handle this case in caller via strip_h1.
    # links
    s = re.sub(r'<a\s+([^>]*?)href="([^"]+)"([^>]*)>(.*?)</a>',
               lambda m: f"[{m.group(4).strip()}]({m.group(2)})",
               s, flags=re.DOTALL | re.IGNORECASE)
    # bold / strong
    s = re.sub(r'</?(?:strong|b)\s*>', '**', s, flags=re.IGNORECASE)
    s = re.sub(r'</?(?:em|i)\s*>', '*', s, flags=re.IGNORECASE)
    # headings
    for level in (1, 2, 3, 4, 5, 6):
        prefix = "#" * level
        s = re.sub(rf'<h{level}\b[^>]*>(.*?)</h{level}>',
                   lambda m, p=prefix: f"\n\n{p} {m.group(1).strip()}\n\n",
                   s, flags=re.DOTALL | re.IGNORECASE)
    # paragraphs and line breaks
    s = re.sub(r'<p\b[^>]*>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'</p\s*>', '\n\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<br\s*/?>', '  \n', s, flags=re.IGNORECASE)
    # lists
    s = re.sub(r'<(?:ol|ul)\b[^>]*>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'</(?:ol|ul)\s*>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<li\b[^>]*>', '- ', s, flags=re.IGNORECASE)
    s = re.sub(r'</li\s*>', '\n', s, flags=re.IGNORECASE)
    # strip remaining tags
    s = re.sub(r'<[^>]+>', '', s)
    # decode entities like &amp; &gt;
    s = html.unescape(s)
    # collapse blank lines
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip() + "\n"


def manifest_path(cdn_url: str) -> str | None:
    return MANIFEST.get(cdn_url)


def write_page(slug: str, info: dict):
    if slug not in PAGE_MAP:
        return
    out_rel, permalink, layout, title = PAGE_MAP[slug]
    out_path = REPO_ROOT / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = info.get("html_chunks") or []
    body = "\n\n".join(html_to_markdown(c) for c in chunks).strip()

    fm = ["---", f"layout: {layout}", f"title: \"{title}\"", f"permalink: {permalink}"]

    if layout == "gallery":
        # Gallery images: skip the first image if it appears to be a logo/icon
        # (we'll filter favicon already, but also skip very obviously non-content paths)
        imgs = info.get("images") or []
        gallery_imgs = []
        for u in imgs:
            local = manifest_path(u)
            if local:
                gallery_imgs.append({"src": local})
        if gallery_imgs:
            fm.append("images:")
            for it in gallery_imgs:
                fm.append(f"  - src: {it['src']}")

    fm.append("---")
    fm.append("")
    out_path.write_text("\n".join(fm) + body + "\n", encoding="utf-8")
    print(f"wrote {out_rel}")


def write_blog_post():
    info = CONTENT.get("blog__2013__5__26__introducing-the-new-varagurorg")
    if not info:
        return
    post_path = REPO_ROOT / "_posts" / "2013-05-26-introducing-the-new-varagurorg.md"
    post_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n\n".join(html_to_markdown(c) for c in (info["html_chunks"] or []))
    fm = [
        "---",
        "layout: post",
        "title: \"Introducing the new varagur.org\"",
        "date: 2013-05-26",
        "permalink: /blog/2013/5/26/introducing-the-new-varagurorg/",
        "---",
        "",
    ]
    post_path.write_text("\n".join(fm) + body + "\n", encoding="utf-8")
    print(f"wrote _posts/{post_path.name}")


def main():
    for slug, info in CONTENT.items():
        write_page(slug, info)
    write_blog_post()


if __name__ == "__main__":
    main()
