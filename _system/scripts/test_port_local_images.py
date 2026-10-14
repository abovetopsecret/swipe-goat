"""python3 test_port_local_images.py: images/<file> paths must reach the theme as assets, not 404."""
import pathlib, tempfile
from port import extract_local_images

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    (d / "images").mkdir(); (d / "out" / "assets").mkdir(parents=True)
    (d / "images" / "hero.jpg").write_bytes(b"jpg")
    body = '<img src="images/hero.jpg"><div style="background-image:url(images/hero.jpg)"></div><img src="images/gone.png">'
    css = '.a{background:url("images/hero.jpg")} .b{background:url(other/images/x.png)}'
    body, css, copied, missing = extract_local_images(body, css, d / "index.html", d / "out", "s")
    assert body.count("{{ 's-hero.jpg' | asset_url }}") == 2, body
    assert 'url("s-hero.jpg")' in css, css
    assert "other/images/x.png" in css, "only the swipe's own images/ folder is rewritten"
    assert missing == ["gone.png"] and 'src="images/gone.png"' in body
    assert (d / "out" / "assets" / "s-hero.jpg").read_bytes() == b"jpg"
print("ok")
