#!/usr/bin/env python3
"""Search and rank brand logo assets for skill workflows.

Usage:
  python3 scripts/logo_search.py OpenAI Anthropic
  python3 scripts/logo_search.py OpenAI --validate
  python3 scripts/logo_search.py OpenAI --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

SVGL_SEARCH_URL = "https://api.svgl.app?search={query}"
SIMPLE_ICONS_URL = "https://cdn.simpleicons.org/{slug}"
HTTP_TIMEOUT_S = 20


@dataclass
class Candidate:
    brand_query: str
    source: str
    title: str
    recommended: str | None
    fallbacks: list[str]
    official_url: str | None
    brand_url: str | None
    score: int


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "logo-search-skill/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def url_exists(url: str) -> bool:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "logo-search-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S):
            return True
    except Exception:
        return False


def slugify(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", query.lower())


def score_title(title: str, query: str) -> int:
    t = title.strip().lower()
    q = query.strip().lower()
    if not t or not q:
        return 0
    if t == q:
        return 100
    if t.replace(" ", "") == q.replace(" ", ""):
        return 95
    if t.startswith(q):
        return 85
    if q in t:
        return 75
    q_words = [w for w in re.split(r"\s+", q) if w]
    if q_words and all(w in t for w in q_words):
        return 65
    return 40


def flatten_asset_links(value) -> list[str]:
    links: list[str] = []
    if isinstance(value, str) and value.startswith("http"):
        links.append(value)
    elif isinstance(value, dict):
        # Keep a stable preference order.
        for key in ("light", "default", "dark"):
            link = value.get(key)
            if isinstance(link, str) and link.startswith("http"):
                links.append(link)
        # Include any other links not already captured.
        for key, link in value.items():
            if key in {"light", "default", "dark"}:
                continue
            if isinstance(link, str) and link.startswith("http") and link not in links:
                links.append(link)
    return links


def build_svgl_candidates(query: str) -> list[Candidate]:
    url = SVGL_SEARCH_URL.format(query=urllib.parse.quote(query))
    try:
        payload = fetch_json(url)
    except Exception:
        return []
    if not isinstance(payload, list):
        return []

    results: list[Candidate] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue

        route_links = flatten_asset_links(item.get("route"))
        wordmark_links = flatten_asset_links(item.get("wordmark"))
        all_links = route_links + [l for l in wordmark_links if l not in route_links]
        recommended = all_links[0] if all_links else None
        fallbacks = all_links[1:] if len(all_links) > 1 else []

        results.append(
            Candidate(
                brand_query=query,
                source="SVGL",
                title=title,
                recommended=recommended,
                fallbacks=fallbacks,
                official_url=item.get("url"),
                brand_url=item.get("brandUrl"),
                score=score_title(title, query),
            )
        )

    return sorted(results, key=lambda c: c.score, reverse=True)


def build_simpleicons_candidate(query: str) -> Candidate | None:
    slug = slugify(query)
    if not slug:
        return None
    url = SIMPLE_ICONS_URL.format(slug=slug)
    if not url_exists(url):
        return None
    return Candidate(
        brand_query=query,
        source="Simple Icons",
        title=query,
        recommended=url,
        fallbacks=[],
        official_url=f"https://simpleicons.org/?q={urllib.parse.quote(query)}",
        brand_url=None,
        score=60,
    )


def validate_svg_url(url: str) -> dict[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "logo-search-skill/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    width = root.attrib.get("width", "missing")
    height = root.attrib.get("height", "missing")
    view_box = root.attrib.get("viewBox", "missing")

    return {
        "width": width,
        "height": height,
        "viewBox": view_box,
        "hasViewBox": "yes" if view_box != "missing" else "no",
    }


def find_candidates(query: str, limit: int) -> list[Candidate]:
    candidates = build_svgl_candidates(query)
    simpleicons = build_simpleicons_candidate(query)
    if simpleicons is not None:
        candidates.append(simpleicons)
    candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    return candidates[:limit]


def to_dict(candidate: Candidate) -> dict:
    return {
        "brand_query": candidate.brand_query,
        "source": candidate.source,
        "title": candidate.title,
        "recommended": candidate.recommended,
        "fallbacks": candidate.fallbacks,
        "official_url": candidate.official_url,
        "brand_url": candidate.brand_url,
        "score": candidate.score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Search and rank logo assets.")
    parser.add_argument("brands", nargs="+", help="Brand names to search")
    parser.add_argument("--limit", type=int, default=3, help="Max candidates per brand (default: 3)")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--validate", action="store_true", help="Validate recommended SVG metadata")
    args = parser.parse_args()

    limit = max(1, min(args.limit, 10))
    output: dict[str, list[dict]] = {}

    for brand in args.brands:
        matches = find_candidates(brand, limit=limit)
        rows: list[dict] = []
        for item in matches:
            row = to_dict(item)
            if args.validate and item.recommended:
                try:
                    row["svg_validation"] = validate_svg_url(item.recommended)
                except Exception as exc:
                    row["svg_validation_error"] = str(exc)
            rows.append(row)
        output[brand] = rows

    if args.json:
        print(json.dumps(output, indent=2))
        return 0

    for brand, rows in output.items():
        print(f"Brand: {brand}")
        if not rows:
            print("  Recommended: none found")
            print("  Note: Try official brand assets manually.")
            print()
            continue

        top = rows[0]
        print(
            f"  Recommended: {top.get('recommended') or 'none'} "
            f"(source={top.get('source')}, title={top.get('title')})"
        )

        fallback_links: list[str] = []
        for row in rows:
            for link in row.get("fallbacks", []):
                if link not in fallback_links:
                    fallback_links.append(link)
            rec = row.get("recommended")
            if rec and rec != top.get("recommended") and rec not in fallback_links:
                fallback_links.append(rec)
        if fallback_links:
            print("  Fallbacks:")
            for link in fallback_links[:5]:
                print(f"    - {link}")
        else:
            print("  Fallbacks: none")

        brand_url = top.get("brand_url")
        official = top.get("official_url")
        print(f"  Official URL: {official or 'unknown'}")
        print(f"  Brand Guide URL: {brand_url or 'unknown'}")
        print("  License/Trademark note: brand assets may require trademark-compliant usage.")
        print("  Implementation note: prefer SVG with viewBox and add descriptive alt text.")

        if args.validate and "svg_validation" in top:
            v = top["svg_validation"]
            print(
                f"  SVG Validation: width={v.get('width')} height={v.get('height')} "
                f"viewBox={v.get('viewBox')} hasViewBox={v.get('hasViewBox')}"
            )
        elif args.validate and "svg_validation_error" in top:
            print(f"  SVG Validation error: {top['svg_validation_error']}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
