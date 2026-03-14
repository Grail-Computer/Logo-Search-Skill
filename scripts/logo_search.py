#!/usr/bin/env python3
"""Search and rank brand logo assets for skill workflows.

Usage:
  python3 scripts/logo_search.py OpenAI Anthropic
  python3 scripts/logo_search.py OpenAI --validate
  python3 scripts/logo_search.py OpenAI --json --prefer wordmark
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

SVGL_SEARCH_URL = "https://api.svgl.app?search={query}"
SIMPLE_ICONS_URL = "https://cdn.simpleicons.org/{slug}"
HTTP_TIMEOUT_S = 20
USER_AGENT = "logo-search-skill/1.1"
HTTP_RETRIES = 3

CURATED_BRANDS: dict[str, dict[str, str | int | list[str] | None]] = {
    "claudecode": {
        "title": "Claude Code",
        "source": "Curated agent icon",
        "recommended": "https://here.now/agenticons/agenticon-claudecode.svg",
        "fallbacks": [],
        "official_url": "https://claude.com/product/claude-code",
        "brand_url": "https://www.anthropic.com/claude-code",
        "score": 108,
        "notes": "Curated product icon fallback for agent UIs when a public Claude Code SVG wordmark is unavailable.",
    },
    "codex": {
        "title": "Codex",
        "source": "Curated agent icon",
        "recommended": "https://here.now/agenticons/agenticon-codex.svg",
        "fallbacks": [],
        "official_url": "https://openai.com/codex/",
        "brand_url": "https://openai.com/brand/",
        "score": 108,
        "notes": "Curated product icon fallback for agent UIs when a public Codex SVG wordmark is unavailable.",
    },
}

QUERY_VARIANTS: dict[str, list[str]] = {
    "claudecode": ["Claude Code", "ClaudeCode", "Claude-Code"],
    "codex": ["Codex", "OpenAI Codex"],
    "opencode": ["OpenCode", "Open Code"],
    "openclaw": ["OpenClaw", "Open Claw"],
    "cursor": ["Cursor"],
    "openai": ["OpenAI", "Open AI"],
    "anthropic": ["Anthropic"],
}


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
    notes: str | None = None


def fetch_json(url: str):
    last_error: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as exc:
            last_error = exc
            if attempt < HTTP_RETRIES - 1:
                time.sleep(0.35 * (attempt + 1))
    raise last_error or RuntimeError(f"request failed: {url}")


def url_exists(url: str) -> bool:
    for attempt in range(HTTP_RETRIES):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S):
                return True
        except Exception:
            if attempt < HTTP_RETRIES - 1:
                time.sleep(0.2 * (attempt + 1))
    return False


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", query.lower())).strip()


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


def preferred_asset_links(route_links: list[str], wordmark_links: list[str], prefer: str) -> list[str]:
    if prefer == "wordmark":
        primary = wordmark_links
        secondary = route_links
    else:
        primary = route_links
        secondary = wordmark_links
    return primary + [link for link in secondary if link not in primary]


def build_query_variants(query: str) -> list[str]:
    variants: list[str] = []
    seen: set[str] = set()
    base = query.strip()
    normalized = normalize_query(query)
    compact = normalized.replace(" ", "")

    for item in [base, normalized.title(), compact, *QUERY_VARIANTS.get(slugify(query), [])]:
        candidate = item.strip()
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        variants.append(candidate)

    return variants


def build_curated_candidates(query: str) -> list[Candidate]:
    curated = CURATED_BRANDS.get(slugify(query))
    if curated is None:
        return []
    return [
        Candidate(
            brand_query=query,
            source=str(curated["source"]),
            title=str(curated["title"]),
            recommended=str(curated["recommended"]) if curated.get("recommended") else None,
            fallbacks=[str(item) for item in curated.get("fallbacks", [])],
            official_url=str(curated["official_url"]) if curated.get("official_url") else None,
            brand_url=str(curated["brand_url"]) if curated.get("brand_url") else None,
            score=int(curated["score"]),
            notes=str(curated["notes"]) if curated.get("notes") else None,
        )
    ]


def build_svgl_candidates(brand_query: str, search_term: str, prefer: str) -> list[Candidate]:
    url = SVGL_SEARCH_URL.format(query=urllib.parse.quote(search_term))
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
        all_links = preferred_asset_links(route_links, wordmark_links, prefer)
        recommended = all_links[0] if all_links else None
        fallbacks = all_links[1:] if len(all_links) > 1 else []

        results.append(
            Candidate(
                brand_query=brand_query,
                source="SVGL",
                title=title,
                recommended=recommended,
                fallbacks=fallbacks,
                official_url=item.get("url"),
                brand_url=item.get("brandUrl"),
                score=score_title(title, brand_query),
            )
        )

    return sorted(results, key=lambda c: c.score, reverse=True)


def build_simpleicons_candidate(brand_query: str, search_term: str) -> Candidate | None:
    slug = slugify(search_term)
    if not slug:
        return None
    url = SIMPLE_ICONS_URL.format(slug=slug)
    if not url_exists(url):
        return None
    return Candidate(
        brand_query=brand_query,
        source="Simple Icons",
        title=search_term,
        recommended=url,
        fallbacks=[],
        official_url=f"https://simpleicons.org/?q={urllib.parse.quote(search_term)}",
        brand_url=None,
        score=60,
        notes="Icon-only fallback. Prefer official brand assets or SVGL when a wordmark is required.",
    )


def validate_svg_url(url: str) -> dict[str, str]:
    last_error: Exception | None = None
    data: bytes | None = None
    for attempt in range(HTTP_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
                data = resp.read()
            break
        except Exception as exc:
            last_error = exc
            if attempt < HTTP_RETRIES - 1:
                time.sleep(0.35 * (attempt + 1))
    if data is None:
        raise last_error or RuntimeError(f"request failed: {url}")

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


def dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[Candidate] = []
    for item in sorted(candidates, key=lambda c: c.score, reverse=True):
        key = (item.source, item.title.lower(), item.recommended or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def find_candidates(query: str, limit: int, prefer: str = "icon") -> list[Candidate]:
    candidates = build_curated_candidates(query)
    for variant in build_query_variants(query):
        candidates.extend(build_svgl_candidates(query, variant, prefer=prefer))
        simpleicons = build_simpleicons_candidate(query, variant)
        if simpleicons is not None:
            candidates.append(simpleicons)
    return dedupe_candidates(candidates)[:limit]


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
        "notes": candidate.notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Search and rank logo assets.")
    parser.add_argument("brands", nargs="+", help="Brand names to search")
    parser.add_argument("--limit", type=int, default=3, help="Max candidates per brand (default: 3)")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--validate", action="store_true", help="Validate recommended SVG metadata")
    parser.add_argument(
        "--prefer",
        choices=("icon", "wordmark"),
        default="icon",
        help="Prefer icon-style marks or wordmarks when a source provides both (default: icon)",
    )
    args = parser.parse_args()

    limit = max(1, min(args.limit, 10))
    output: dict[str, list[dict]] = {}

    for brand in args.brands:
        matches = find_candidates(brand, limit=limit, prefer=args.prefer)
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
        if top.get("notes"):
            print(f"  Note: {top['notes']}")

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
