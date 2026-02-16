# Logo Source Guidance

## Source Priority

1. Official brand pages / press kits
- Best source for legal clarity and correct latest branding.
- Use when available.

2. SVGL (`https://svgl.app/`)
- Fast for developer workflows and common SaaS logos.
- Good default for web UI implementation.
- API endpoint for search: `https://api.svgl.app?search=<brand>`.
- Typical fields: `route`, `wordmark`, `url`, and sometimes `brandUrl`.

3. Simple Icons (`https://simpleicons.org/`)
- Good for uniform icon sets.
- Usually icon-focused variants, not always official wordmarks.
- CDN endpoint: `https://cdn.simpleicons.org/<slug>`.
- Prefer as fallback when an official or SVGL source is unavailable.

## Selection Checklist

- Source trust: official first, then reputable aggregator.
- Asset quality: valid SVG with proper `viewBox`.
- Visual consistency: variant matches nearby logos in the same UI.
- Legal note: include trademark/licensing caveat when needed.

## Licensing Notes

- Brand logos are typically trademarks even when downloadable.
- Treat logos as brand assets, not generic open media.
- If terms are not obvious, flag for manual legal/brand confirmation.

## Fast Verification

1. Discover candidates:
- `python3 scripts/logo_search.py OpenAI Anthropic`

2. Validate recommended SVG:
- `python3 scripts/logo_search.py OpenAI --validate`
- `python3 scripts/check_svg.py /path/to/logo.svg`
