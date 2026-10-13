"""Minimal hand-written pages that mirror the markup the parsers rely on."""

ITCH_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Free assets</title>
<item>
  <plainTitle>Tiny Maze Tiles</plainTitle><title>Tiny Maze Tiles [Free]</title>
  <link>https://alice.itch.io/tiny-maze</link><price>$0.00</price>
  <imageurl>https://img.itch.zone/a.png</imageurl>
  <description><![CDATA[Pixel maze tiles 16x16 <img src="x.png"/>]]></description>
</item>
<item>
  <plainTitle>Space Ships</plainTitle><title>Space Ships</title>
  <link>https://bob.itch.io/ships</link><price>$0.00</price>
  <imageurl>https://img.itch.zone/b.png</imageurl>
  <description><![CDATA[Sci-fi ship sprites]]></description>
</item>
</channel></rss>"""

ITCH_DATA_JSON = """{"title": "Tiny Maze Tiles", "price": "$0.00",
"authors": [{"name": "Alice", "url": "https://alice.itch.io"}],
"tags": ["2d", "pixel-art", "tileset"], "screenshots": ["https://img.itch.zone/s1.png"]}"""

ITCH_PAGE = """<html><body>
<div class="formatted_description user_formatted">
  <p>Tiles for maze games.</p>
  <p>License: free for commercial use. Credit is appreciated but not required.</p>
</div>
<div class="upload_list_widget base_widget">
  <div class="upload"><div class="upload_name"><strong class="name">maze.zip</strong>
  <span class="file_size"><span>12 kB</span></span></div></div>
</div>
<div class="game_info_panel_widget base_widget"><table><tbody>
  <tr><td>Author</td><td><a href="https://alice.itch.io">Alice</a></td></tr>
  <tr><td>Asset license</td><td>Creative Commons Zero v1.0 Universal</td></tr>
  <tr><td>Rating</td><td>5 stars</td></tr>
</tbody></table></div>
</body></html>"""

OGA_SEARCH = """<html><body>
<div class="view-content"><div class="views-row"><a href="/forumtopic/sidebar">Forum topic</a></div></div>
<div class="view view-art"><div class="view-header"> Displaying 1 - 2 of 42 </div>
<div class="view-content">
  <div class="views-row art-previews-inline">
    <span class="art-preview-title"><a href="/content/maze-pack">Maze Pack</a></span>
    <div class="field-name-field-art-preview"><img src="https://opengameart.org/thumb1.png"></div>
  </div>
  <div class="views-row art-previews-inline">
    <span class="art-preview-title"><a href="/content/ghost-sprites">Ghost Sprites</a></span>
  </div>
</div></div>
</body></html>"""

OGA_PAGE = """<html><body>
<div class="field field-name-title"><h2>Maze Pack</h2></div>
<div class="field field-name-author-submitter"><div class="field-items">
  <span class="username"><a href="/users/carol">Carol</a></span></div></div>
<div class="field field-name-post-date">Monday, January 1, 2024</div>
<div class="field field-name-field-art-type"><a href="#">2D Art</a></div>
<div class="field field-name-field-art-tags"><a href="#">maze</a><a href="#">16x16</a></div>
<div class="field field-name-field-art-licenses"><div class="field-items">
  <div class="license-icon"><a href="http://creativecommons.org/licenses/by/4.0/">
  <div class="license-name">CC-BY 4.0</div></a></div></div></div>
<div class="field field-name-body"><div class="field-items"><p>A maze tileset.</p></div></div>
<div class="field field-name-field-art-attribution"><div class="field-items">Credit Carol.</div></div>
<div class="field field-name-field-art-files"><div class="field-items">
  <span class="file"><a href="https://opengameart.org/sites/default/files/maze.png"
     type="image/png; length=2048">maze.png</a>
     <span class="dlcount">[<span class="dlcount-number">99</span> download(s)]</span></span>
</div></div>
</body></html>"""
