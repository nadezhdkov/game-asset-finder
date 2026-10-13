# CLAUDE.md

Guidance for working on **game-asset-finder**, a single-file Python MCP server
(`server.py`) that searches itch.io and OpenGameArt.org for free 2D game assets.
User-facing documentation lives in [README.md](README.md).

## Layout

- `server.py`: the whole server. Inline PEP 723 dependencies; run with
  `uv run --script server.py` (stdio transport).
- `smoke.py`: live end-to-end check against both sites.
- `tests/`: offline pytest suite; `tests/fixtures.py` holds hand-written pages
  that mirror the markup each parser relies on.
- `pyproject.toml`: dev tooling; its `dependencies` must equal the inline
  metadata in `server.py` (a test enforces it).
- `.github/`: CI, PR checks, auto-merge, weekly live smoke test, Dependabot.
- `docs/CHANGELOG.md`: user-visible changes, Keep a Changelog format.

## Commands

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run pytest                                    # offline tests (what CI runs)
uv run --script smoke.py                         # live test (~30 s, real network)
uv run --script server.py                        # start the server on stdio
claude mcp list                                  # check the registered server connects
```

`uv run pytest` is offline and is what pull requests run. `smoke.py` hits the
real sites, so run it sparingly (it also runs weekly in CI). When site markup
changes, update `tests/fixtures.py` to the new structure alongside the parser fix.

## CI and merging

Pull requests must pass `CI / Lint`, `CI / Test (Python 3.11|3.12|3.13)`,
`PR checks / PR title` and `PR checks / Changelog`. Merging is label-driven:
a maintainer adds `automerge` and GitHub squash-merges once checks pass; new
outside commits revoke it. Keep workflow permissions per job, pin Actions by
commit SHA, and never check out PR code in `pull_request_target` workflows
(verify with `uvx zizmor --offline .github/workflows/`).

## Rules that must not regress

- **Respect robots.txt.** Never request itch.io `/search` or `/game/download/`,
  and never automate itch.io purchases or "pay what you want" flows. itch.io
  search stays tag-feed based; itch.io downloads stay manual (`download_game_asset`
  returns a manual link, `record_asset_credit` logs credits afterwards).
- **Keep the per-host delays** in `HOST_DELAY` (itch.io 2 s, OpenGameArt 10 s
  from its `Crawl-delay`) and the 24 h cache. All page requests go through
  `_get()`; file downloads must also wait on the per-host lock.
- **Never present a licence as verified when it is not.** OpenGameArt licences
  come from the structured field; itch.io licences come from the optional
  "Asset license" field, otherwise only as quoted excerpts marked unverified.
- **Every download records attribution** in `assets.json` / `CREDITS.md` via
  `_record()`.
- **Treat downloaded archives as untrusted.** Keep `_safe_extract()`'s path
  traversal check and the size/count limits.

## Changelog and versions

- Every change that affects behaviour, tool contracts, output, dependencies or
  docs users rely on gets an entry under `## [Unreleased]` in
  `docs/CHANGELOG.md`, in the same commit, under Added / Changed / Deprecated /
  Removed / Fixed / Security.
- On release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, add a fresh
  empty `[Unreleased]`, update the compare links at the bottom, and set
  `__version__` in `server.py` to match. Semantic Versioning: tool contract
  breaks bump MAJOR (MINOR while 0.x), new tools/options bump MINOR, fixes
  bump PATCH.
- Commit subjects follow Conventional Commits (`feat:`, `fix:`, `docs:`…).

## Conventions

- MCP Python SDK **2.x**: `from mcp.server.mcpserver import MCPServer`
  (FastMCP was renamed in 2.0). Tools are `async` functions decorated with
  `@mcp.tool()`; their docstrings and type hints become the advertised schema,
  so keep them accurate and concise.
- Site parsing is HTML/RSS scraping with BeautifulSoup and ElementTree. When a
  site changes markup, fix the selector at its single parsing function
  (`_search_itch`, `_itch_details`, `_search_oga`, `_oga_details`) and re-run
  `smoke.py`.
- Keep tool output compact: summaries in search results, details only in
  `get_game_asset`, descriptions clipped with `_clip()`.
- Write code, comments and docs in English.
