"""Offline tests: parsing, licences, credits, archive safety and the MCP protocol."""

import json
import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

import server
from tests import fixtures

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def pages(monkeypatch):
    """Serve fixture pages instead of the network and record requested URLs."""
    requested: list[str] = []

    async def fake_get(url: str, *, cache: bool = True) -> str:
        requested.append(url)
        if url.startswith("https://itch.io/") and ".xml" in url:
            return fixtures.ITCH_FEED if "page=" not in url else "<rss><channel></channel></rss>"
        if url.endswith("/data.json"):
            return fixtures.ITCH_DATA_JSON
        if "itch.io" in url:
            return fixtures.ITCH_PAGE
        if "art-search-advanced" in url:
            return fixtures.OGA_SEARCH
        if "opengameart.org/content/" in url:
            return fixtures.OGA_PAGE
        raise AssertionError(f"unexpected request {url}")

    monkeypatch.setattr(server, "_get", fake_get)
    return requested


async def test_itch_search_uses_tag_feeds_and_filters_text(pages):
    result = await server.search_game_assets(query="maze", tags=["Pixel Art"], source="itch")
    itch = result["itch"]
    assert itch["tags_used"] == ["2d", "pixel-art"]
    assert [r["title"] for r in itch["results"]] == ["Tiny Maze Tiles"]
    assert all("/search" not in url for url in pages), "itch.io /search is disallowed by robots.txt"


async def test_oga_search_skips_sidebar_rows_and_maps_filters(pages):
    result = await server.search_game_assets(query="maze", source="opengameart", licenses=["cc0", "bogus"])
    oga = result["opengameart"]
    assert oga["total_matches"] == 42
    assert [r["title"] for r in oga["results"]] == ["Maze Pack", "Ghost Sprites"]
    assert oga["unknown_licenses_ignored"] == ["bogus"]
    assert "field_art_licenses_tid%5B%5D=4" in pages[0]


async def test_itch_details_prefer_declared_licence_field(pages):
    details = await server.get_game_asset("https://alice.itch.io/tiny-maze?ref=x")
    assert details["license"] == "Creative Commons Zero v1.0 Universal"
    assert details["authors"][0]["name"] == "Alice"
    assert details["files"] == [{"name": "maze.zip", "size": "12 kB"}]
    assert any("commercial" in excerpt for excerpt in details["license_excerpts"])
    assert "rating" in details and "Rating" not in details["info"]


async def test_oga_details_read_structured_fields(pages):
    details = await server.get_game_asset("https://opengameart.org/content/maze-pack")
    assert details["author"] == "Carol"
    assert details["licenses"] == [{"name": "CC-BY 4.0", "url": "http://creativecommons.org/licenses/by/4.0/"}]
    assert details["attribution_instructions"] == "Credit Carol."
    assert details["files"][0] == {
        "name": "maze.png",
        "url": "https://opengameart.org/sites/default/files/maze.png",
        "bytes": 2048,
        "downloads": 99,
    }


async def test_unsupported_hosts_are_rejected():
    with pytest.raises(ValueError):
        await server.get_game_asset("https://example.com/asset")


async def test_itch_downloads_stay_manual(pages, tmp_path):
    result = await server.download_game_asset("https://alice.itch.io/tiny-maze", str(tmp_path))
    assert result["downloaded"] == [] and result["manual_download"] == "https://alice.itch.io/tiny-maze"
    assert not any("/game/download" in url for url in pages)


async def test_credit_ledger_summarises_large_folders(pages, tmp_path):
    files = [f"maze-pack/tile{i}.png" for i in range(20)]
    details = await server.get_game_asset("https://opengameart.org/content/maze-pack")
    server._record(tmp_path, details, files, "maze-pack")
    server._record(tmp_path, details, files, "maze-pack")  # re-recording replaces, not duplicates
    ledger = json.loads((tmp_path / "assets.json").read_text())
    credits = (tmp_path / "CREDITS.md").read_text()
    assert len(ledger) == 1 and ledger[0]["licenses"] == ["CC-BY 4.0"]
    assert "- Files: maze-pack/ (20 files)" in credits
    assert "- Attribution: Credit Carol." in credits


async def test_record_credit_for_manual_itch_download(pages, tmp_path):
    await server.record_asset_credit("https://alice.itch.io/tiny-maze", str(tmp_path), ["maze/maze.zip"])
    credits = (tmp_path / "CREDITS.md").read_text()
    assert "Creative Commons Zero v1.0 Universal" in credits and "maze/maze.zip" in credits


def test_extraction_skips_os_junk_and_refuses_traversal(tmp_path):
    good, evil = tmp_path / "good.zip", tmp_path / "evil.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("tiles/a.png", "x")
        zf.writestr("__MACOSX/tiles/._a.png", "x")
        zf.writestr("tiles/.DS_Store", "x")
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../../escaped.txt", "x")
    assert server._safe_extract(good, tmp_path / "out") == ["tiles/a.png"]
    with pytest.raises(ValueError, match="unsafe path"):
        server._safe_extract(evil, tmp_path / "evil")
    assert not (tmp_path.parent / "escaped.txt").exists()


def test_licence_excerpts_quote_only_relevant_sentences():
    text = "Great tiles. Licensed CC0, no credit needed. Made with love."
    assert server._license_excerpts(text) == ["Licensed CC0, no credit needed."]


def test_inline_script_dependencies_match_pyproject():
    inline = re.search(r"# dependencies = (\[.*\])", (ROOT / "server.py").read_text()).group(1)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert json.loads(inline) == project["dependencies"]
    assert project["version"] == server.__version__


def test_mcp_protocol_lists_tools():
    """Start the real server over stdio and speak MCP to it."""
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:

        def send(message: dict) -> None:
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()

        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            }
        )
        init = json.loads(proc.stdout.readline())
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = json.loads(proc.stdout.readline())["result"]["tools"]
    finally:
        proc.kill()
    assert init["result"]["serverInfo"] == {"name": "game-assets", "version": server.__version__}
    names = {tool["name"] for tool in tools}
    assert names == {"search_game_assets", "get_game_asset", "download_game_asset", "record_asset_credit"}
