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
import zipfile
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
    assert downloaded["files"]["count"] == 1 and downloaded["missing_requested_files"] == ["missing.png"], downloaded
    assert (dest / "CREDITS.md").exists() and json.loads((dest / "assets.json").read_text())
    print("downloaded:", downloaded["files"], "->", dest)
    check_extraction(dest)
    print("OK")


def check_extraction(dest: Path) -> None:
    """Offline: OS junk is skipped and path traversal is refused."""
    good, evil = dest / "good.zip", dest / "evil.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("tiles/a.png", "x")
        zf.writestr("__MACOSX/tiles/._a.png", "x")
        zf.writestr("tiles/.DS_Store", "x")
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../../escaped.txt", "x")
    assert server._safe_extract(good, dest / "good") == ["tiles/a.png"]
    try:
        server._safe_extract(evil, dest / "evil")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal was not refused")
    print("extraction checks passed")


if __name__ == "__main__":
    asyncio.run(main())
