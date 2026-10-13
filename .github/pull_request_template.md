## What does this change?

<!-- One or two sentences. Link the issue if there is one: Fixes #123 -->

## Checklist

- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`…)
- [ ] Entry added under `[Unreleased]` in `docs/CHANGELOG.md` (or the change is CI/docs-only)
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pytest` pass locally
- [ ] Still follows each site's robots.txt (no itch.io `/search` or automated itch.io downloads, crawl delays kept)
- [ ] Tested against the live sites with `uv run --script smoke.py` if parsing changed
