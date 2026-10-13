<div align="center">

<img src="docs/assets/logo.svg" alt="game-asset-finder logo" width="140">

# game-asset-finder

**Find free 2D game assets on itch.io and OpenGameArt, check their licences, and keep credits, straight from your AI agent.**

[![CI](https://github.com/nadezhdkov/game-asset-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/nadezhdkov/game-asset-finder/actions/workflows/ci.yml)
[![Live smoke test](https://github.com/nadezhdkov/game-asset-finder/actions/workflows/live-smoke.yml/badge.svg)](https://github.com/nadezhdkov/game-asset-finder/actions/workflows/live-smoke.yml)
[![Version](https://img.shields.io/github/v/tag/nadezhdkov/game-asset-finder?label=version&color=6c5ce7)](docs/CHANGELOG.md)
[![License: MIT](https://img.shields.io/github/license/nadezhdkov/game-asset-finder?color=ffd166)](LICENSE)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-server-6c5ce7)](https://modelcontextprotocol.io/)
[![uv](https://img.shields.io/badge/uv-managed-de5fe9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![itch.io](https://img.shields.io/badge/itch.io-assets-fa5c5c?logo=itchdotio&logoColor=white)](https://itch.io/game-assets)
[![OpenGameArt](https://img.shields.io/badge/OpenGameArt-assets-3a7bd5)](https://opengameart.org/)

[Tools](#tools) · [Installation](#installation) · [Site rules](#site-rules) · [Contributing](CONTRIBUTING.md) · [Changelog](docs/CHANGELOG.md)

</div>

---

An [MCP](https://modelcontextprotocol.io/) server that gives Claude Code (or any
MCP client) tools to search for free **2D game assets**, inspect their licences
and attribution requirements, download them, and keep a ready-to-use credits file.

```text
You:    Find a CC0 16x16 platformer tileset and a character for my game.
Agent:  search_game_assets → get_game_asset → download_game_asset
        ✓ saved to assets/, licence checked, CREDITS.md updated
```

## Tools

| Tool | What it does |
|---|---|
| `search_game_assets` | Search both sites by text, tags (`pixel-art`, `tileset`, `platformer`, `top-down`, `character`, `ui`, `16x16`…), type (`2d`, `music`, `sfx`, `texture`), licence (OpenGameArt: `cc0`, `cc-by-4.0`, `oga-by-4.0`…), sort order and page. |
| `get_game_asset` | Details for one asset: authors, licence (declared field, or licence excerpts from the itch.io description), attribution instructions, tags, description and file list. |
| `download_game_asset` | Download OpenGameArt files into `dest_dir/<asset>/`, safely extract ZIPs (skipping `__MACOSX`/`.DS_Store` junk and deleting the archive unless `keep_archive` is set) and record credits. Results report a file count and sample rather than every file. |
| `record_asset_credit` | Record credits for an asset obtained manually (for example from itch.io). |

Credits are kept in `dest_dir/assets.json` (data) and `dest_dir/CREDITS.md`
(ready for a game's credits screen). Licences such as CC-BY and OGA-BY require
attribution; CC0 does not, but the record still tracks where each asset came from.

## Installation

Requires [uv](https://docs.astral.sh/uv/). Dependencies (`mcp`, `httpx`,
`beautifulsoup4`) are declared inline in `server.py` and installed by uv.

```bash
git clone https://github.com/nadezhdkov/game-asset-finder.git
claude mcp add --scope user game-assets -- uv run --script "$PWD/game-asset-finder/server.py"
claude mcp list   # should show game-assets ✔ Connected
```

Remove it with `claude mcp remove --scope user game-assets`. Any other MCP
client can run the same command (`uv run --script server.py`) over stdio.

## Site rules

The server follows both sites' `robots.txt`:

- **itch.io** disallows `/search` and `/game/download/` for bots. Searches use
  the public tag-browse RSS feeds (text queries are filtered locally), and
  **itch.io files are downloaded by a person in a browser**; call
  `record_asset_credit` afterwards. Requests to itch.io are spaced 2 s apart.
- **OpenGameArt** sets `Crawl-delay: 10`, so requests there are spaced 10 s
  apart. Pages are cached for 24 h in `~/.cache/game-asset-finder`.

itch.io licences are not always structured: when the author fills in the
"Asset license" field it is used; otherwise the tool returns the description
sentences that mention licensing and marks the licence as unverified.

## Development

```bash
uv run ruff check . && uv run ruff format --check .   # lint and format
uv run pytest                                         # offline tests, no network
uv run --script smoke.py                              # live check against both sites (~30 s)
```

Every pull request runs lint, offline tests on Python 3.11–3.13, an MCP
protocol test, a changelog check and a Conventional Commits title check.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the review and auto-merge process.

## Safety limits

Files up to 300 MiB; ZIPs up to 1 GiB uncompressed and 20,000 entries; ZIP
paths that would escape the destination folder are rejected.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## License

[MIT](LICENSE). This licence covers the server's code only; every asset you
find or download keeps its own licence, recorded in `CREDITS.md`.
