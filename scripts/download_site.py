#!/usr/bin/env python3
"""
Mirror varagur.org content + images for the GitHub Pages migration.

For each URL in the live sitemap:
  - Save the raw HTML to scripts/cache/html/<slug>.html
  - Find every Squarespace CDN image, download it to assets/images/<slug>/<filename>
  - Write a manifest mapping original CDN URL -> local path

Run from the repo root: python3 scripts/download_site.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_HTML = REPO_ROOT / "scripts" / "cache" / "html"
ASSETS_IMG = REPO_ROOT / "assets" / "images"
MANIFEST_PATH = REPO_ROOT / "scripts" / "cache" / "image_manifest.json"

SITEMAP_URL = "https://www.varagur.org/sitemap.xml"
USER_AGENT = "varagur-migration/1.0 (+https://varagur.org)"

# URLs to skip — Squarespace internal redirects + auto-generated empty category pages
SKIP_PATTERNS = [
    re.compile(r"/blog/category/"),
    re.compile(r"^https?://[^/]+/(home-nav|about/home|media/home|home)$"),
]


def fetch(url: str) -> bytes:
    # Use curl to avoid Python's macOS cert-bundle issues.
    result = subprocess.run(
        ["curl", "-sSL", "--fail", "-A", USER_AGENT, "--max-time", "60", url],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed ({result.returncode}): {result.stderr.decode('utf-8', errors='replace').strip()}")
    return result.stdout


def parse_sitemap(xml: bytes) -> list[str]:
    urls = re.findall(rb"<loc>([^<]+)</loc>", xml)
    out = []
    for u in urls:
        s = u.decode("utf-8").replace("http://", "https://")
        if any(p.search(s) for p in SKIP_PATTERNS):
            continue
        out.append(s)
    return out


def url_to_slug(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    if not path:
        return "index"
    return path.replace("/", "__")


class ImgExtractor(HTMLParser):
    """Collect Squarespace CDN image URLs and the document's <title>."""

    def __init__(self):
        super().__init__()
        self.images: list[str] = []
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "img":
            for k in ("src", "data-src", "data-image"):
                v = d.get(k)
                if v and "squarespace-cdn.com" in v:
                    # strip query params (Squarespace adds ?format=...&content-type=...)
                    clean = v.split("?")[0]
                    if clean not in self.images:
                        self.images.append(clean)
                    break
        if tag == "source":
            srcset = d.get("srcset") or d.get("data-srcset") or ""
            for part in srcset.split(","):
                u = part.strip().split(" ")[0]
                if "squarespace-cdn.com" in u:
                    clean = u.split("?")[0]
                    if clean not in self.images:
                        self.images.append(clean)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            t = data.strip()
            if t:
                self.title = t


def download_image(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = fetch(url)
        if len(data) < 100:
            print(f"  ! tiny response ({len(data)} bytes) for {url}", file=sys.stderr)
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  ! failed: {url} ({e})", file=sys.stderr)
        return False


def main():
    CACHE_HTML.mkdir(parents=True, exist_ok=True)
    ASSETS_IMG.mkdir(parents=True, exist_ok=True)

    print(f"fetching sitemap: {SITEMAP_URL}")
    urls = parse_sitemap(fetch(SITEMAP_URL))
    urls.append("https://www.varagur.org/")  # root not in sitemap
    print(f"  {len(urls)} pages to mirror")

    manifest: dict[str, str] = {}

    for i, url in enumerate(urls, 1):
        slug = url_to_slug(url)
        html_path = CACHE_HTML / f"{slug}.html"
        print(f"[{i}/{len(urls)}] {url}  ->  {slug}")

        if html_path.exists() and html_path.stat().st_size > 0:
            html_bytes = html_path.read_bytes()
        else:
            try:
                html_bytes = fetch(url)
            except Exception as e:
                print(f"  ! page fetch failed: {e}", file=sys.stderr)
                continue
            html_path.write_bytes(html_bytes)
            time.sleep(0.5)  # be polite

        parser = ImgExtractor()
        try:
            parser.feed(html_bytes.decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"  ! parse error: {e}", file=sys.stderr)
            continue

        if parser.title:
            print(f"  title: {parser.title}")
        print(f"  images: {len(parser.images)}")

        for img_url in parser.images:
            filename = urllib.parse.unquote(img_url.rsplit("/", 1)[-1])
            # keep file extension reasonable
            filename = re.sub(r"[^A-Za-z0-9._+\-]", "_", filename)
            local_path = ASSETS_IMG / slug / filename
            if download_image(img_url, local_path):
                rel = "/" + str(local_path.relative_to(REPO_ROOT))
                manifest[img_url] = rel
                time.sleep(0.1)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"\nmanifest: {len(manifest)} images written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
