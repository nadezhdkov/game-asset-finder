"""Regenerate the pixel-art logo.

Run: python docs/assets/make_logo.py docs/assets/logo.svg
"""

import math
import sys
from pathlib import Path

N, S = 32, 8
grid = {}


def put(x, y, c):
    if 0 <= x < N and 0 <= y < N:
        grid[(x, y)] = c


cx, cy = 12.5, 12.5
for y in range(N):
    for x in range(N):
        d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
        if d <= 7.2:
            put(x, y, "glass_dark" if d > 6.0 else "glass")
        elif d <= 9.3:
            put(x, y, "ring_dark" if (x + 0.5 - cx) + (y + 0.5 - cy) > 5 else "ring")

STAR = [
    "......Y......",
    ".....YYY.....",
    ".....YYY.....",
    "YYYYYYYYYYYYY",
    ".YYYYYYYYYYY.",
    "..YYYYYYYYY..",
    "...YYYYYYY...",
    "...YYYYYYY...",
    "..YYYYYYYYY..",
    "..YYYY.YYYY..",
    ".YYY.....YYY.",
]
ox, oy = 6, 7
star = {(ox + i, oy + j) for j, row in enumerate(STAR) for i, ch in enumerate(row) if ch == "Y"}
for p in star:
    x, y = p
    edge = (x + 1, y) not in star or (x, y + 1) not in star
    put(x, y, "star_dark" if edge and (x - ox > 6 or y - oy > 6) else "star")
for p in [(ox + 5, oy + 4), (ox + 4, oy + 5)]:
    put(*p, "star_light")
for x, y in [(8, 7), (7, 8), (7, 9), (9, 6)]:
    if grid.get((x, y), "").startswith("glass"):
        put(x, y, "glint")

# Handle: 3 px thick, 45 degrees, ending inside the icon.
for t in range(0, 9):
    bx, by = 19 + t, 19 + t
    for dx, dy in [(0, 0), (1, 0), (0, 1), (-1, 1), (1, -1)]:
        p = (bx + dx, by + dy)
        if grid.get(p, "").startswith(("ring", "glass")):
            continue
        shade = "handle_dark" if dx - dy > 0 else ("handle_light" if dx - dy < 0 else "handle")
        put(*p, shade if t > 1 else "ring_dark")

for sx, sy, size in [(26, 5, 2), (4, 27, 1), (28, 14, 1)]:
    for k in range(-size, size + 1):
        put(sx + k, sy, "spark")
        put(sx, sy + k, "spark")

filled = dict(grid)
for (x, y), c in filled.items():
    if c == "spark":
        continue
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        p = (x + dx, y + dy)
        if p not in filled:
            grid[p] = "outline"

colors = {
    "glass": "#7b6cf6",
    "glass_dark": "#5b4bd8",
    "glint": "#ece8ff",
    "ring": "#e2e4f3",
    "ring_dark": "#a9add0",
    "star": "#ffd166",
    "star_dark": "#f29e2e",
    "star_light": "#fff3c4",
    "handle": "#a8653a",
    "handle_dark": "#6e3d20",
    "handle_light": "#cf8a52",
    "spark": "#ffffff",
    "outline": "#140f24",
}
rects = "".join(
    f'<rect x="{x * S}" y="{y * S}" width="{S}" height="{S}" fill="{colors[c]}"/>'
    for (x, y), c in sorted(grid.items(), key=lambda kv: (kv[0][1], kv[0][0]))
)
HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" '
    'viewBox="0 0 256 256" shape-rendering="crispEdges">\n'
    "  <title>game-asset-finder</title>\n"
    '  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#2b2152"/><stop offset="1" stop-color="#171230"/>'
    "</linearGradient></defs>\n"
    '  <rect width="256" height="256" rx="40" fill="url(#bg)"/>\n'
)
Path(sys.argv[1]).write_text(f"{HEADER}  {rects}\n</svg>\n")
