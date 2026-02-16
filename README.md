# Logo Search Skill

Find official, high-quality logos fast (SVG-first), with source links, fallback options, and basic trademark-aware guidance for production UI work.

## Why this skill

This skill helps teams avoid the common logo workflow pain points:
- Wasting time searching random sources
- Picking inconsistent logo variants
- Missing SVG quality checks (`viewBox`, scaling)
- Shipping assets without clear source context

`Logo-Search-Skill` gives you a repeatable flow for discovering, validating, and integrating brand logos.

## Install

```bash
npx skills add Grail-Computer/Logo-Search-Skill
```

You can also install from the full URL:

```bash
npx skills add https://github.com/Grail-Computer/Logo-Search-Skill
```

## Quick Start

Run a search for one or more brands:

```bash
python3 scripts/logo_search.py OpenAI Anthropic
```

Run with SVG validation for the top recommendation:

```bash
python3 scripts/logo_search.py OpenAI Anthropic --validate
```

JSON output mode:

```bash
python3 scripts/logo_search.py OpenAI Anthropic --validate --json
```

## What you get

For each brand, the skill returns:
- Recommended logo asset URL
- Fallback asset URLs
- Source ranking
- Official/brand-reference URLs when available
- SVG metadata checks (when `--validate` is enabled)

## Skill Workflow

1. Confirm brand + variant requirements (icon vs wordmark, light/dark).
2. Search trusted sources in priority order.
3. Validate candidate quality (especially SVG readiness).
4. Return implementation-ready recommendations with notes.

## Project Structure

- `SKILL.md` - Skill behavior and usage guidance
- `agents/openai.yaml` - UI metadata for skill tooling
- `scripts/logo_search.py` - Runnable logo discovery + ranking tool
- `scripts/check_svg.py` - SVG metadata checker
- `references/sources.md` - Source and licensing guidance

## Example Output

```text
Brand: OpenAI
  Recommended: https://svgl.app/library/openai.svg
  Fallbacks:
    - https://svgl.app/library/openai_dark.svg
    - https://svgl.app/library/openai_wordmark_light.svg
  Official URL: https://openai.com/
  Brand Guide URL: https://openai.com/brand/
```

## Compatibility

The repository follows the open Agent Skills format and is designed to work well with common skill-enabled agents.

## Attribution

This skill is fully developed by **FastClaw** and the **Grail.Computer** team.

- FastClaw repo: https://github.com/Grail-Computer/FastClaw
- Grail: https://grail.computer

## Hire Grail as an AI Employee

You can hire Grail as an AI Employee by:
- Emailing us at **yash@grail.computer**
- Visiting **https://hire.grail.computer**

## Notes

- Brand logos are usually trademarked assets.
- If licensing or brand-use terms are unclear, treat the result as requiring legal/brand review before publication.
