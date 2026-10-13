# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.3,<3", "httpx>=0.27", "beautifulsoup4>=4.12"]
# ///
"""Live smoke test against itch.io and OpenGameArt (takes ~30 s because of crawl delays).

Run: uv run --script smoke.py [dest_dir]
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server  # noqa: E402

OGA_ASSET = "https://opengameart.org/content/a-platformer-in-the-forest"


async def main() -> None:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="gaf-smoke-"))
    found = await server.search_game_assets(tags=["pixel-art", "platformer"], limit=3)
    for site in ("itch", "opengameart"):
        part = found[site]
        assert "error" not in part, part
        print(f"{site}: {len(part['results'])} results")
    itch_url = found["itch"]["results"][0]["url"]
    details = await server.get_game_asset(itch_url)
    print("itch details:", details["title"], "| license:", details["license"] or details["license_excerpts"][:1])
    refused = await server.download_game_asset(itch_url, str(dest))
    assert refused["downloaded"] == [] and refused["manual_download"], refused
    downloaded = await server.download_game_asset(OGA_ASSET, str(dest), files=["sheet.png", "missing.png"])
    assert downloaded["files"] and downloaded["missing_requested_files"] == ["missing.png"], downloaded
    assert (dest / "CREDITS.md").exists() and json.loads((dest / "assets.json").read_text())
    print("downloaded:", downloaded["files"], "->", dest)
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
