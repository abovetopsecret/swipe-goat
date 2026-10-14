#!/usr/bin/env python3
"""Targeted deep-clean transforms on a swipe page (stdlib only, edits in place).

Does: <button>-><a>; remove known tracking <script> tags; ensure viewport meta.
Does NOT do general dead-CSS tree-shaking (leave that to Codex's judgment per page).

Usage: python3 clean.py <page.html> [more...]
"""
import re, sys, pathlib

TRACKERS = ("googletagmanager", "google-analytics", "gtag(", "connect.facebook.net",
            "fbq(", "hotjar", "static.hotjar", "segment.com", "cdn.segment",
            "clarity.ms", "doubleclick")

def clean(html: str) -> str:
    # <button ...>...</button>  ->  <a href="#" ...>...</a>  (drop type=, preserve display)
    # A bare <a> is display:inline, so a width:100%/centered button collapses & left-aligns.
    # Merge button-like rendering so layout (full-width, centered text) survives.
    BTN_FIX = "display:inline-block;text-align:center;box-sizing:border-box;"
    def btn(m):
        attrs = re.sub(r'\stype\s*=\s*["\'][^"\']*["\']', "", m.group(1))
        if re.search(r'style\s*=\s*"', attrs, re.I):
            attrs = re.sub(r'(style\s*=\s*")', r'\1' + BTN_FIX, attrs, count=1, flags=re.I)
        elif re.search(r"style\s*=\s*'", attrs, re.I):
            attrs = re.sub(r"(style\s*=\s*')", r'\1' + BTN_FIX, attrs, count=1, flags=re.I)
        else:
            attrs = attrs + f' style="{BTN_FIX}"'
        return f'<a href="#"{attrs}>'
    html = re.sub(r"<button\b([^>]*)>", btn, html, flags=re.I)
    html = re.sub(r"</button>", "</a>", html, flags=re.I)

    # remove tracking <script> blocks (with or without src)
    def drop_script(m):
        block = m.group(0)
        return "" if any(t in block.lower() for t in TRACKERS) else block
    html = re.sub(r"<script\b[^>]*>.*?</script>", drop_script, html,
                  flags=re.I | re.S)
    html = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", drop_script, html, flags=re.I)

    # ensure viewport meta
    if not re.search(r'name=["\']viewport["\']', html, re.I) and "<head" in html.lower():
        html = re.sub(r"(<head[^>]*>)",
                      r'\1\n<meta name="viewport" content="width=device-width, '
                      r'initial-scale=1">', html, count=1, flags=re.I)
    return html

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        p.write_text(clean(p.read_text(encoding="utf-8", errors="replace")),
                     encoding="utf-8")
        print(f"  cleaned {p.name}")
