# game-asset-finder

An MCP server that gives Claude Code (or any MCP client) tools to find free
**2D game assets** on **itch.io** and **OpenGameArt.org**, check their licences,
and download them with attribution recorded.

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

## Installation

Requires [uv](https://docs.astral.sh/uv/). Dependencies (`mcp`, `httpx`,
`beautifulsoup4`) are declared inline in `server.py` and installed by uv.

```bash
claude mcp add --scope user game-assets -- uv run --script /absolute/path/to/server.py
claude mcp list   # should show game-assets ✔ Connected
```

Remove it with `claude mcp remove --scope user game-assets`.

## Testing

```bash
uv run --script smoke.py            # live check against both sites (~30 s)
```

## Safety limits

Files up to 300 MiB; ZIPs up to 1 GiB uncompressed and 20,000 entries; ZIP
paths that would escape the destination folder are rejected.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## License

[MIT](LICENSE). This licence covers the server's code only; every asset you
find or download keeps its own licence, recorded in `CREDITS.md`.
