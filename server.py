# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.3,<3", "httpx>=0.27", "beautifulsoup4>=4.12"]
# ///
"""MCP server that finds 2D game assets on itch.io and OpenGameArt.

It follows each site's robots.txt: itch.io's /search and /game/download/ are
off limits, so itch results come from the public tag-browse RSS feeds and
itch files must be downloaded by a person in a browser. OpenGameArt asks for
a 10-second crawl delay, which every OpenGameArt request honours. Responses
are cached on disk for a day to keep traffic low.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode, urljoin, urlparse
from xml.etree import ElementTree

import logging

import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

USER_AGENT = "game-asset-finder/0.1 (personal asset search; Claude Code MCP)"
CACHE_DIR = Path.home() / ".cache" / "game-asset-finder"
CACHE_TTL = 24 * 3600
# Minimum seconds between requests to one host.
HOST_DELAY = {"itch.io": 2.0, "opengameart.org": 10.0}
MAX_FILE_BYTES = 300 * 1024 * 1024
MAX_EXTRACT_BYTES = 1024 * 1024 * 1024
MAX_EXTRACT_FILES = 20_000

OGA = "https://opengameart.org"
OGA_TYPES = {"2d": "9", "concept": "7273", "texture": "14", "music": "12", "sfx": "13", "3d": "10"}
OGA_LICENSES = {
    "cc0": "4",
    "cc-by-3.0": "2",
    "cc-by-4.0": "17981",
    "cc-by-sa-3.0": "3",
    "cc-by-sa-4.0": "17982",
    "oga-by-3.0": "10310",
    "oga-by-4.0": "31772",
    "gpl-2.0": "5",
    "gpl-3.0": "6",
}
ITCH_TYPE_TAG = {"2d": "2d", "music": "music", "sfx": "sound-effects"}
LICENSE_HINT = re.compile(
    r"(?i)\b(cc0|cc[- ]by(?:[- ]sa)?(?: ?\d\.\d)?|creative commons|public domain|licen[cs]e|"
    r"credit|attribution|commercial|royalty[- ]free|redistribut|resell)"
)

logging.getLogger("httpx").setLevel(logging.WARNING)
mcp = MCPServer("game-assets", instructions="Find free 2D game assets on itch.io and OpenGameArt; check licences with get_game_asset and record credits.")
_last_request: dict[str, float] = {}
_locks: dict[str, asyncio.Lock] = {}


# --- HTTP with politeness and caching ---------------------------------------


def _host(url: str) -> str:
    host = urlparse(url).hostname or ""
    return "itch.io" if host == "itch.io" or host.endswith(".itch.io") else host


async def _get(url: str, *, cache: bool = True) -> str:
    """GET text with per-host spacing, one 429 retry and a one-day disk cache."""
    key = CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
    if cache and key.exists() and time.time() - key.stat().st_mtime < CACHE_TTL:
        return key.read_text(encoding="utf-8")
    host = _host(url)
    lock = _locks.setdefault(host, asyncio.Lock())
    async with lock:
        for attempt in range(2):
            wait = HOST_DELAY.get(host, 1.0) - (time.monotonic() - _last_request.get(host, 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30
            ) as client:
                response = await client.get(url)
            _last_request[host] = time.monotonic()
            if response.status_code == 429 and attempt == 0:
                retry = response.headers.get("retry-after", "")
                await asyncio.sleep(min(float(retry) if retry.isdigit() else 15.0, 60.0))
                continue
            response.raise_for_status()
            break
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key.write_text(response.text, encoding="utf-8")
    return response.text


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _license_excerpts(text: str, limit: int = 4) -> list[str]:
    """Sentences that mention licensing or credit terms, verbatim."""
    sentences = re.split(r"(?<=[.!?])\s+|\s*•\s*", text)
    found = [s.strip() for s in sentences if LICENSE_HINT.search(s)]
    return [_clip(s, 300) for s in found[:limit]]


# --- itch.io ----------------------------------------------------------------


async def _search_itch(query: str, tags: list[str], asset_type: str, free_only: bool,
                       sort: str, page: int, limit: int) -> dict:
    tag_slugs = [_slug(t) for t in tags if _slug(t)]
    if asset_type in ITCH_TYPE_TAG and ITCH_TYPE_TAG[asset_type] not in tag_slugs:
        tag_slugs.insert(0, ITCH_TYPE_TAG[asset_type])
    path = "/game-assets"
    if sort == "newest":
        path += "/newest"
    if free_only:
        path += "/free"
    path += "".join(f"/tag-{t}" for t in tag_slugs[:3])
    words = [w.lower() for w in re.findall(r"\w+", query)]
    results: list[dict] = []
    scanned = 0
    # Feeds hold ~30 items per page; scan a few pages when filtering by text.
    pages = range(page, page + (3 if words else 1))
    for p in pages:
        url = f"https://itch.io{path}.xml" + (f"?page={p}" if p > 1 else "")
        try:
            root = ElementTree.fromstring(await _get(url))
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                break
            raise
        items = root.findall("./channel/item")
        if not items:
            break
        for item in items:
            scanned += 1
            title = item.findtext("plainTitle") or item.findtext("title") or ""
            summary = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text(" ", strip=True)
            haystack = f"{title} {summary}".lower()
            if words and not all(w in haystack for w in words):
                continue
            link = item.findtext("link") or ""
            results.append({
                "source": "itch.io",
                "title": title,
                "url": link,
                "author": urlparse(link).hostname.split(".")[0] if link else None,
                "price": item.findtext("price"),
                "summary": _clip(summary, 160),
                "thumbnail": item.findtext("imageurl"),
                "license": "unknown - call get_game_asset (itch licenses are free text)",
            })
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
    return {
        "source": "itch.io",
        "feed": f"https://itch.io{path}",
        "tags_used": tag_slugs[:3],
        "items_scanned": scanned,
        "results": results,
        "next_page": page + len(pages) if results else None,
        "note": "itch.io forbids automated /search, so results come from tag-browse feeds; "
                "use specific tags (e.g. pixel-art, tileset, platformer, top-down, character, ui, 16x16).",
    }


async def _itch_details(url: str) -> dict:
    base = url.split("?")[0].rstrip("/")
    data = json.loads(await _get(base + "/data.json"))
    soup = BeautifulSoup(await _get(base), "html.parser")
    info: dict[str, str] = {}
    panel = soup.select_one(".game_info_panel_widget")
    if panel:
        for row in panel.select("tr"):
            cells = row.select("td")
            if len(cells) == 2:
                info[_text(cells[0])] = _text(cells[1])
    description = _text(soup.select_one(".formatted_description"))
    uploads = [
        {"name": _text(u.select_one(".upload_name .name")), "size": _text(u.select_one(".file_size"))}
        for u in soup.select(".upload_list_widget .upload")
    ]
    return {
        "source": "itch.io",
        "title": html.unescape(data.get("title", "")),
        "url": base,
        "authors": data.get("authors", []),
        "price": data.get("price"),
        "tags": data.get("tags", []),
        "info": {k: v for k, v in info.items() if k not in ("Rating",)},
        "rating": info.get("Rating"),
        # Authors may fill the optional "Asset license" field; otherwise only free text exists.
        "license": info.get("Asset license"),
        "license_excerpts": _license_excerpts(description),
        "license_note": ("Declared in the page's Asset license field." if info.get("Asset license") else
                         "No declared licence field; read the excerpts and description before use. "
                         "When none are present, ask the author or treat as all rights reserved."),
        "description": _clip(description, 1500),
        "files": uploads,
        "screenshots": data.get("screenshots", [])[:4],
        "download": f"Download manually in a browser: {base} (itch.io disallows automated downloads). "
                    "Then call record_asset_credit to log attribution.",
    }


# --- OpenGameArt ------------------------------------------------------------


async def _search_oga(query: str, tags: list[str], asset_type: str, licenses: list[str],
                      sort: str, page: int, limit: int) -> dict:
    params: list[tuple[str, str]] = [("keys", query)]
    if asset_type in OGA_TYPES:
        params.append(("field_art_type_tid[]", OGA_TYPES[asset_type]))
    unknown = [lic for lic in licenses if lic.lower() not in OGA_LICENSES]
    for lic in licenses:
        if lic.lower() in OGA_LICENSES:
            params.append(("field_art_licenses_tid[]", OGA_LICENSES[lic.lower()]))
    if tags:
        params += [("field_art_tags_tid", ", ".join(tags)), ("field_art_tags_tid_op", "and")]
    params += [
        ("sort_by", {"popular": "count", "newest": "created"}.get(sort, "score")),
        ("sort_order", "DESC"),
        ("items_per_page", "24"),
        ("page", str(max(0, page - 1))),
    ]
    url = f"{OGA}/art-search-advanced?" + urlencode(params)
    soup = BeautifulSoup(await _get(url), "html.parser")
    header = _text(soup.select_one(".view-header"))
    total = re.search(r"of\s+([\d,]+)", header)
    results = []
    # Sidebar views share .views-row; art results are the inline previews.
    for row in soup.select(".views-row.art-previews-inline"):
        if len(results) >= limit:
            break
        link = row.select_one(".art-preview-title a")
        if not link:
            continue
        image = row.select_one(".field-name-field-art-preview img")
        results.append({
            "source": "opengameart",
            "title": _text(link),
            "url": urljoin(OGA, link["href"]),
            "thumbnail": image.get("src") if image else None,
            "license": "filtered: " + ", ".join(licenses) if licenses else "call get_game_asset",
        })
    return {
        "source": "opengameart",
        "search_url": url,
        "total_matches": int(total.group(1).replace(",", "")) if total else len(results),
        "results": results,
        "unknown_licenses_ignored": unknown,
        "next_page": page + 1 if results else None,
        "note": "OpenGameArt asks for a 10 s delay between requests, so each call there takes ~10 s.",
    }


async def _oga_details(url: str) -> dict:
    soup = BeautifulSoup(await _get(url), "html.parser")

    def field(name: str):
        return soup.select_one(f".field-name-{name} .field-items")

    licenses = []
    for item in soup.select(".field-name-field-art-licenses .license-icon"):
        anchor = item.select_one("a")
        licenses.append({"name": _text(item.select_one(".license-name")), "url": anchor.get("href") if anchor else None})
    files = []
    for anchor in soup.select(".field-name-field-art-files a[href]"):
        kind = anchor.get("type", "")
        size = re.search(r"length=(\d+)", kind)
        count = anchor.find_parent("span", class_="file")
        downloads = count.select_one(".dlcount-number") if count else None
        files.append({
            "name": _text(anchor),
            "url": urljoin(OGA, anchor["href"]),
            "bytes": int(size.group(1)) if size else None,
            "downloads": int(_text(downloads)) if downloads and _text(downloads).isdigit() else None,
        })
    author_node = soup.select_one(".field-name-author-submitter .username")
    title = soup.select_one(".field-name-title h2") or soup.select_one("h2")
    return {
        "source": "opengameart",
        "title": _text(title),
        "url": url,
        "author": _text(author_node),
        "author_line": _text(field("author-submitter")),
        "posted": _text(soup.select_one(".field-name-post-date")),
        "art_type": [_text(a) for a in soup.select(".field-name-field-art-type a")],
        "tags": [_text(a) for a in soup.select(".field-name-field-art-tags a")],
        "licenses": licenses,
        "attribution_instructions": _text(field("field-art-attribution")) or None,
        "description": _clip(_text(field("body")), 1500),
        "files": files,
        "favorites": _text(soup.select_one(".field-name-favorites .field-items")) or None,
    }


# --- Credits ledger ---------------------------------------------------------


def _record(dest: Path, details: dict, saved: list[str]) -> Path:
    """Append one entry to assets.json and regenerate CREDITS.md from it."""
    dest.mkdir(parents=True, exist_ok=True)
    ledger_path = dest / "assets.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if details["source"] == "opengameart":
        authors = [details.get("author")] if details.get("author") else []
        licenses = [lic["name"] for lic in details.get("licenses", [])]
        attribution = details.get("attribution_instructions")
    else:
        authors = [a.get("name") for a in details.get("authors", [])]
        licenses = ([details["license"]] if details.get("license") else
                    details.get("license_excerpts") or ["UNVERIFIED - see source page"])
        attribution = None
    entry = {
        "title": details.get("title"),
        "source": details.get("source"),
        "url": details.get("url"),
        "authors": authors,
        "licenses": licenses,
        "attribution_instructions": attribution,
        "files": saved,
        "recorded": date.today().isoformat(),
    }
    ledger = [e for e in ledger if e.get("url") != entry["url"]] + [entry]
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    lines = ["# Asset credits", "", "Generated by game-asset-finder from assets.json.", ""]
    for e in ledger:
        lines += [
            f"## {e['title']}",
            f"- Source: {e['url']}",
            f"- Author(s): {', '.join(a for a in e['authors'] if a) or 'unknown'}",
            f"- License: {'; '.join(e['licenses']) or 'unknown'}",
        ]
        if e.get("attribution_instructions"):
            lines.append(f"- Attribution: {e['attribution_instructions']}")
        if e.get("files"):
            lines.append(f"- Files: {', '.join(e['files'])}")
        lines.append("")
    (dest / "CREDITS.md").write_text("\n".join(lines))
    return ledger_path


def _safe_extract(archive: Path, target: Path) -> list[str]:
    """Extract a zip without path traversal and within size/count limits."""
    extracted = []
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if len(members) > MAX_EXTRACT_FILES or sum(m.file_size for m in members) > MAX_EXTRACT_BYTES:
            raise ValueError(f"{archive.name} is too large to extract safely")
        root = target.resolve()
        for member in members:
            path = (target / member.filename).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"{archive.name} contains an unsafe path: {member.filename}")
        zf.extractall(target)
        extracted = [m.filename for m in members if not m.is_dir()]
    return extracted


# --- Tools ------------------------------------------------------------------


@mcp.tool()
async def search_game_assets(
    query: str = "",
    tags: list[str] | None = None,
    source: Literal["all", "itch", "opengameart"] = "all",
    asset_type: Literal["2d", "music", "sfx", "texture", "concept", "any"] = "2d",
    licenses: list[str] | None = None,
    free_only: bool = True,
    sort: Literal["relevance", "popular", "newest"] = "popular",
    page: int = 1,
    limit: int = 12,
) -> dict:
    """Search free game assets on itch.io and OpenGameArt.org for 2D games.

    query: words that must appear (itch: matched in title/summary; OpenGameArt: site keyword search).
    tags: itch.io browse tags such as pixel-art, tileset, platformer, top-down, character,
      ui, 16x16, fantasy, sci-fi (up to 3 are combined; itch searching is tag-based).
      On OpenGameArt all given tags must match.
    licenses: OpenGameArt filter, any of cc0, cc-by-3.0, cc-by-4.0, cc-by-sa-3.0, cc-by-sa-4.0,
      oga-by-3.0, oga-by-4.0, gpl-2.0, gpl-3.0. itch.io licenses are free text; check with get_game_asset.
    free_only: itch.io only free assets (OpenGameArt is always free).
    Results are summaries; call get_game_asset for licence, attribution and files before using anything.
    OpenGameArt calls take ~10 s each because of its crawl delay.
    """
    tags = tags or []
    licenses = licenses or []
    limit = max(1, min(limit, 30))
    out: dict = {"query": query}
    tasks = {}
    if source in ("all", "itch"):
        tasks["itch"] = _search_itch(query, tags, asset_type, free_only, sort, page, limit)
    if source in ("all", "opengameart"):
        tasks["opengameart"] = _search_oga(query, tags, asset_type, licenses, sort, page, limit)
    done = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for name, result in zip(tasks, done):
        out[name] = {"error": f"{type(result).__name__}: {result}"} if isinstance(result, Exception) else result
    return out


@mcp.tool()
async def get_game_asset(url: str) -> dict:
    """Details for one itch.io or OpenGameArt asset page: authors, licence(s) or licence
    excerpts, attribution instructions, tags, description and the file list."""
    if _host(url) == "itch.io":
        return await _itch_details(url)
    if _host(url) == "opengameart.org":
        return await _oga_details(url)
    raise ValueError("Only itch.io and opengameart.org asset pages are supported.")


@mcp.tool()
async def download_game_asset(
    url: str,
    dest_dir: str,
    files: list[str] | None = None,
    extract_zip: bool = True,
) -> dict:
    """Download files of an OpenGameArt asset into dest_dir/<asset-slug>/ and record
    attribution in dest_dir/assets.json and dest_dir/CREDITS.md.

    files: file names to fetch (default: all). Zip files are extracted safely when
    extract_zip is true. itch.io assets must be downloaded manually in a browser;
    use record_asset_credit afterwards.
    """
    if _host(url) == "itch.io":
        return {
            "downloaded": [],
            "manual_download": url.split("?")[0],
            "reason": "itch.io disallows automated downloads (robots.txt) and many packs use a "
                      "pay-what-you-want flow. Open the page in a browser, download, then call "
                      "record_asset_credit with the same dest_dir.",
        }
    details = await _oga_details(url)
    dest = Path(dest_dir).expanduser().resolve()
    target = dest / _slug(details["title"] or urlparse(url).path)
    target.mkdir(parents=True, exist_ok=True)
    wanted = [f for f in details["files"] if not files or f["name"] in files]
    missing = sorted(set(files or []) - {f["name"] for f in details["files"]})
    saved: list[str] = []
    for item in wanted:
        if item["bytes"] and item["bytes"] > MAX_FILE_BYTES:
            raise ValueError(f"{item['name']} is larger than {MAX_FILE_BYTES // 2**20} MiB")
        name = Path(item["name"]).name
        path = target / name
        host = _host(item["url"])
        async with _locks.setdefault(host, asyncio.Lock()):
            wait = HOST_DELAY.get(host, 1.0) - (time.monotonic() - _last_request.get(host, 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=120) as client:
                async with client.stream("GET", item["url"]) as response:
                    response.raise_for_status()
                    size = 0
                    with path.open("wb") as handle:
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_FILE_BYTES:
                                handle.close()
                                path.unlink(missing_ok=True)
                                raise ValueError(f"{name} exceeded {MAX_FILE_BYTES // 2**20} MiB")
                            handle.write(chunk)
            _last_request[host] = time.monotonic()
        saved.append(str(path.relative_to(dest)))
        if extract_zip and name.lower().endswith(".zip"):
            folder = target / Path(name).stem
            for member in _safe_extract(path, folder):
                saved.append(str((folder / member).relative_to(dest)))
    ledger = _record(dest, details, saved)
    return {
        "title": details["title"],
        "licenses": details["licenses"],
        "attribution_instructions": details["attribution_instructions"],
        "saved_to": str(target),
        "files": saved,
        "missing_requested_files": missing,
        "credits": str(dest / "CREDITS.md"),
        "ledger": str(ledger),
    }


@mcp.tool()
async def record_asset_credit(url: str, dest_dir: str, files: list[str] | None = None) -> dict:
    """Record attribution for an asset you obtained manually (e.g. from itch.io) in
    dest_dir/assets.json and dest_dir/CREDITS.md. files: paths relative to dest_dir."""
    details = await get_game_asset(url)
    dest = Path(dest_dir).expanduser().resolve()
    ledger = _record(dest, details, files or [])
    return {"recorded": details.get("title"), "credits": str(dest / "CREDITS.md"), "ledger": str(ledger)}


if __name__ == "__main__":
    mcp.run()
