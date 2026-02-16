---
name: logo-search-skill
description: Find official, high-quality brand logos/icons (SVG/PNG) quickly with source links and licensing notes. Use when adding provider logos (OpenAI, Anthropic, etc.) to product UI, docs, or marketing assets.
---

# Logo Search Skill

## Overview
Use this skill when a user asks for company/product logos, especially for UI implementation. The goal is to return usable assets fast (prefer SVG), with trustworthy sources and licensing notes.

## Workflow

1. Confirm requirements
- Brand/product names and exact variants (wordmark vs symbol).
- Preferred formats (`svg` first, then `png` fallback).
- Style constraints (monochrome, filled, outlined, light/dark usage).
- Delivery target (web app, mobile app, slides, docs).

2. Search in this priority order
- Existing project assets (avoid duplicate imports and inconsistent variants).
- `https://svgl.app/` for developer-ready SVG packs.
- Official brand pages/press kits from the company website.
- `https://simpleicons.org/` for icon-style marks when brand permits.

3. Validate each candidate
- Confirm source is official or widely trusted.
- Check SVG quality: clean paths, valid `viewBox`, no raster image embedding.
- Check visual fit at small sizes (16px, 24px, 32px).
- Note licensing/trademark constraints when known.

4. Return an implementation-ready result
- Provide 2-3 ranked options per brand.
- Include direct source links and why each option is preferred.
- Recommend default + fallback option.
- Include integration notes (size, color mode, accessibility label).

## CLI Quick Start

Use this script for fast, repeatable lookups:

```bash
python3 scripts/logo_search.py OpenAI Anthropic
```

With SVG metadata validation on the recommended asset:

```bash
python3 scripts/logo_search.py OpenAI Anthropic --validate
```

## Output Template
Use this structure in responses:

- `Brand`: <name>
- `Recommended`: <asset link + reason>
- `Fallbacks`: <asset link(s)>
- `License/Trademark note`: <short note>
- `Implementation note`: <size/color/accessibility recommendation>

## Guardrails
- Do not claim trademark rights ownership.
- If licensing is unclear, explicitly mark it as "needs legal/brand review".
- Prefer official brand resources over third-party mirrors.
- Avoid low-quality or inconsistent logo variants unless user explicitly requests them.

## Resources
- Read `references/sources.md` for source-specific selection and licensing checks.
- Use `scripts/logo_search.py` to discover ranked logo candidates from trusted sources.
- Use `scripts/check_svg.py` to inspect SVG metadata quickly before recommending an asset.
