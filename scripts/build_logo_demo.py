#!/usr/bin/env python3
"""Build a static demo page by replacing brand placeholders with local logo assets.

Usage:
  python3 scripts/build_logo_demo.py assets/demo/names.html assets/demo/logos.html
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from logo_search import USER_AGENT, find_candidates, slugify

PLACEHOLDER_RE = re.compile(
    r"<span(?P<before>[^>]*?)\sdata-logo-brand=(?P<quote>['\"])(?P<brand>.+?)(?P=quote)(?P<after>[^>]*)>(?P<label>.*?)</span>",
    re.IGNORECASE | re.DOTALL,
)
HTTP_TIMEOUT_S = 20
HTTP_RETRIES = 3
STATE_RE = re.compile(
    r'(?P<open><(?P<tag>[a-z0-9]+)\b[^>]*\bdata-logo-demo-state=(?P<quote>["\'])before(?P=quote)[^>]*>)(?P<label>.*?)(?P<close></(?P=tag)>)',
    re.IGNORECASE | re.DOTALL,
)


def guess_extension(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".svg", ".png", ".webp", ".jpg", ".jpeg"):
        if path.endswith(ext):
            return ext
    return ".svg"


def download_file(url: str, destination: Path) -> None:
    last_error: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
                destination.write_bytes(resp.read())
            return
        except Exception as exc:
            last_error = exc
            if attempt < HTTP_RETRIES - 1:
                time.sleep(0.35 * (attempt + 1))
    raise last_error or RuntimeError(f"request failed: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace brand placeholders with downloaded logo assets.")
    parser.add_argument("input_html", help="HTML file containing <span data-logo-brand=\"...\"> placeholders")
    parser.add_argument("output_html", help="Path to write the transformed HTML file")
    parser.add_argument(
        "--assets-dir",
        help="Directory for downloaded logo assets (default: <output dir>/logos)",
    )
    parser.add_argument(
        "--prefer",
        choices=("icon", "wordmark"),
        default="wordmark",
        help="Prefer icon marks or wordmarks when available (default: wordmark)",
    )
    parser.add_argument("--limit", type=int, default=5, help="Max candidate search depth per brand (default: 5)")
    args = parser.parse_args()

    input_path = Path(args.input_html).resolve()
    output_path = Path(args.output_html).resolve()
    assets_dir = Path(args.assets_dir).resolve() if args.assets_dir else output_path.parent / "logos"

    if not input_path.exists():
        print(f"error: file not found: {input_path}", file=sys.stderr)
        return 1

    source = input_path.read_text(encoding="utf-8")
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, tuple[str, str]] = {}
    failures: list[str] = []
    summary: list[str] = []

    def replace(match: re.Match[str]) -> str:
        brand = html.unescape(match.group("brand")).strip()
        if not brand:
            failures.append("unknown")
            return match.group(0)

        cached = downloaded.get(brand)
        if cached is None:
            candidates = find_candidates(brand, limit=max(1, min(args.limit, 10)), prefer=args.prefer)
            if not candidates or not candidates[0].recommended:
                failures.append(brand)
                return match.group(0)

            candidate = candidates[0]
            extension = guess_extension(candidate.recommended)
            filename = f"{slugify(brand) or 'logo'}{extension}"
            asset_path = assets_dir / filename
            try:
                download_file(candidate.recommended, asset_path)
            except Exception as exc:
                failures.append(f"{brand}: {exc}")
                return match.group(0)

            relative_path = os.path.relpath(asset_path, start=output_path.parent).replace(os.sep, "/")
            downloaded[brand] = (relative_path, candidate.recommended)
            summary.append(f"{brand} -> {relative_path} ({candidate.source})")
            cached = downloaded[brand]

        relative_path, _ = cached
        alt_text = html.escape(f"{brand} logo", quote=True)
        src = html.escape(relative_path, quote=True)
        return f'<img src="{src}" alt="{alt_text}" class="brand-logo" loading="lazy" decoding="async">'

    transformed = PLACEHOLDER_RE.sub(replace, source)
    transformed = STATE_RE.sub(
        lambda match: f"{match.group('open').replace('before', 'after', 1)}After{match.group('close')}",
        transformed,
        count=1,
    )
    output_path.write_text(transformed, encoding="utf-8")

    for row in summary:
        print(row)

    print(f"Wrote {output_path}")

    if failures:
        print("Unresolved placeholders:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
