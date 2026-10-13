# Changelog

All notable changes to game-asset-finder are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Offline test suite (`uv run pytest`): parsing against hand-written page
  fixtures, licence handling, credits ledger, archive safety, robots.txt
  guarantees, dependency sync between `server.py` and `pyproject.toml`, and an
  MCP protocol handshake against the real server.
- `pyproject.toml` with dev tooling (pytest, Ruff) for `uv sync` / `uv run`.
- GitHub Actions: lint and offline tests on Python 3.11–3.13 for every pull
  request, Conventional Commits PR title and changelog checks, label-driven
  auto-merge that is revoked when outside contributors push new commits, a
  weekly live smoke test, and Dependabot for Actions (pinned by commit SHA).
- `CONTRIBUTING.md`, pull request and issue templates, and `CODEOWNERS`.
- Pixel-art logo (`docs/assets/logo.svg`, `logo.png`) and a redesigned README
  with a centred header and badges.

### Changed

- Code formatted and linted with Ruff (no behaviour change).

## [0.2.0] - 2026-10-13

### Added

- `download_game_asset` accepts `keep_archive` to keep a downloaded ZIP next
  to its extracted contents.
- `smoke.py` checks ZIP extraction offline: OS metadata entries are skipped
  and path traversal is refused.
- `docs/CHANGELOG.md`, and an explicit server version reported to MCP
  clients and in the User-Agent.

### Changed

- ZIP archives are deleted after successful extraction by default.
- `download_game_asset` returns a file `count` and a `sample` instead of
  every file path, keeping tool results small for large packs.
- `CREDITS.md` lists large asset folders by file count instead of naming
  every file.

### Fixed

- `__MACOSX/`, `._*`, `.DS_Store`, `Thumbs.db` and `desktop.ini` entries are
  no longer extracted from downloaded archives.

## [0.1.0] - 2026-10-13

### Added

- MCP server with four tools: `search_game_assets`, `get_game_asset`,
  `download_game_asset` and `record_asset_credit`.
- itch.io search through public tag-browse RSS feeds, with asset details from
  `data.json`, the info panel (including the optional "Asset license" field)
  and licence excerpts from the description.
- OpenGameArt search with art-type and licence filters, and asset details
  with structured licences, attribution instructions and file lists.
- OpenGameArt downloads with safe ZIP extraction and size limits.
- Attribution ledger: `assets.json` and a generated `CREDITS.md`.
- robots.txt compliance: no itch.io `/search` or automated downloads,
  per-host request spacing (itch.io 2 s, OpenGameArt 10 s crawl delay) and a
  24-hour response cache.
- `smoke.py` live test, README and `CLAUDE.md`.
- MIT license.

[Unreleased]: https://github.com/nadezhdkov/game-asset-finder/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/nadezhdkov/game-asset-finder/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nadezhdkov/game-asset-finder/releases/tag/v0.1.0
