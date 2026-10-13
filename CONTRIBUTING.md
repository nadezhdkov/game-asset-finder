# Contributing

Thanks for helping! Bug reports, site-change reports and pull requests are all
welcome.

## Setup

```bash
git clone https://github.com/nadezhdkov/game-asset-finder.git
cd game-asset-finder
uv sync            # installs runtime and dev dependencies
```

## Before opening a pull request

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest                      # offline: parsing, credits, archive safety, MCP protocol
uv run --script smoke.py           # only if you changed site parsing (hits the real sites)
```

- **Respect each site's robots.txt.** Never add itch.io `/search` requests or
  automated itch.io downloads, and keep the per-host request delays and cache.
  Pull requests that remove these will not be merged.
- **Never present a licence as verified** unless it comes from a structured
  licence field.
- **Add a changelog entry** under `## [Unreleased]` in
  [docs/CHANGELOG.md](docs/CHANGELOG.md). CI/docs-only changes can get the
  `skip-changelog` label from a maintainer instead.
- **Title the PR with [Conventional Commits](https://www.conventionalcommits.org/)**,
  e.g. `fix: parse new OpenGameArt file list markup` or `feat: add licence filter for itch.io`.
- When site markup changes, add or update a fixture in `tests/fixtures.py`
  that reproduces the new structure, and fix the single parsing function for it.

## What CI checks

| Check | Workflow |
|---|---|
| Lint + format (Ruff) | `CI / Lint` |
| Offline tests on Python 3.11, 3.12, 3.13 | `CI / Test (Python 3.x)` |
| Conventional Commits PR title | `PR checks / PR title` |
| `docs/CHANGELOG.md` updated | `PR checks / Changelog` |

All of them are required before merging. A weekly `Live smoke test` checks the
real sites separately so pull requests never depend on them.

## Review and auto-merge

1. A maintainer reviews the pull request.
2. When it is ready, the maintainer adds the **`automerge`** label.
3. GitHub squash-merges it automatically as soon as every required check passes.

If new commits are pushed by an outside contributor after the label was added,
auto-merge is switched off and the label removed, so every merged change has
been seen by a maintainer. Only maintainers can add labels.

Forked pull requests from first-time contributors need a maintainer's approval
before their workflows run (GitHub's default).
