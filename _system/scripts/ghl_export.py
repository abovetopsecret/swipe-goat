#!/usr/bin/env python3
"""Package a finished swipe (standalone index.html) into a GHL Custom-HTML package.

GHL behaviors this works around:
  - A Custom HTML element keeps <style> but STRIPS <script>  -> CSS inline, JS to footer.
  - The tracking footer strips <link rel=stylesheet>          -> never external CSS links.

Emits into <page-dir>/ghl/:
  page-html-all-in-one.html  -> paste into a GHL Custom HTML element (no <script>)
  page-tracking.html         -> paste into Page Settings -> Tracking Code -> Footer
  page-html.html / page-css.css -> 3-slot fallback

Fonts: a single-file capture inlines its web fonts as base64 @font-face, which blows
GHL's ~85-100KB element budget. By default this STRIPS base64 @font-face blocks and
prepends the @import/@font-face from <page-dir>/ghl-fonts.css (or --fonts-css). The
capture's tiny src:local() "...Placeholder" @font-face metric-matchers are kept.
Pass --keep-base64-fonts to leave the base64 fonts inline (only if you're under budget).

Usage:
  python3 ghl_export.py <page.html> [--cdn https://assets.brand.com]
                        [--fonts-css ghl-fonts.css] [--keep-base64-fonts] [--slug NAME]
"""
import argparse, pathlib, re

FULLBLEED = (".ghl-swipe-root{position:relative;left:50%;right:50%;margin-left:-50vw;"
             "margin-right:-50vw;width:100vw;max-width:100vw;padding:0;isolation:isolate}"
             ".ghl-swipe-root,.ghl-swipe-root *{box-sizing:border-box}.ghl-swipe-root>*{max-width:100%}")

SHIM = ("// kill GHL ancestor padding so the .ghl-swipe-root full-bleed breaks out\n"
        "(function(){function k(){var r=document.querySelector('.ghl-swipe-root');if(!r)return;"
        "var n=r.parentElement;while(n&&n!==document.body){['padding-top','padding-bottom',"
        "'padding-left','padding-right','margin-top','margin-bottom'].forEach(function(p){"
        "n.style.setProperty(p,'0','important')});n=n.parentElement}if(document.body){"
        "document.body.style.setProperty('margin','0','important');"
        "document.body.style.setProperty('padding','0','important')}}"
        "if(document.readyState!=='loading')k();else document.addEventListener('DOMContentLoaded',k);})();")

# A full @import statement. The URL/quoted string may contain semicolons
# (Google Fonts css2 URLs are full of them: family=Inter:wght@400;500;...), so we must
# NOT stop at the first ';'. Match the whole url(...)/quoted form, then any media
# query, up to the terminating ';'. A naive r'@import[^;]+;' shatters these URLs.
IMPORT_RE = re.compile(
    r"@import\s+(?:url\(\s*(?:'[^']*'|\"[^\"]*\"|[^)]*)\s*\)|'[^']*'|\"[^\"]*\")[^;]*;",
    re.I)

FONTFACE_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.I | re.S)

def _is_code(block, tag):
    # <script type="application/ld+json"> and friends are data, not code.
    # Concatenated into the page JS, one is a syntax error that stops every
    # script in the file, so they stay in the markup.
    if tag.lower() != "script":
        return True
    m = re.match(r'(?is)<script\b[^>]*\btype\s*=\s*["\']?([^"\'\s>]+)', block)
    return not m or m.group(1).lower() in ("text/javascript", "application/javascript")

def split_blocks(html, tag):
    pat = re.compile(r'<%s\b[^>]*>.*?</%s>' % (tag, tag), re.I | re.S)
    blocks = [b for b in pat.findall(html) if _is_code(b, tag)]
    inner = [re.match(r'(?is)<%s\b[^>]*>(.*)</%s>' % (tag, tag), b).group(1) for b in blocks]
    return inner, pat.sub(lambda m: '' if _is_code(m.group(0), tag) else m.group(0), html)

def body_inner(no_js):
    """Return just the <body>'s inner HTML. Single-file captures often omit </body>
    (and even <body>); never leak a literal <body>/<html> tag into the fragment."""
    m = re.search(r'(?is)<body\b[^>]*>(.*?)</body>', no_js)
    if m:
        return m.group(1).strip()
    s = re.sub(r'(?is)^.*?</head>', '', no_js)      # drop everything through </head>
    s = re.sub(r'(?is)^\s*<body\b[^>]*>', '', s)     # strip a leading <body ...> open tag
    s = re.sub(r'(?is)</body\s*>|</html\s*>', '', s) # strip stray closers
    return s.strip()

def strip_base64_fontfaces(css):
    n = [0]
    def drop(m):
        block = m.group(0)
        if "base64," in block or "data:" in block:
            n[0] += 1
            return ""
        return block
    return FONTFACE_RE.sub(drop, css), n[0]

def cdnify(s, base):
    base = base.rstrip("/")
    s = re.sub(r'(src|href)=(["\'])(/?(?:images|assets|_next|media)/[^"\']+)\2',
               lambda m: '%s=%s%s/%s%s' % (m.group(1), m.group(2), base,
                                           m.group(3).lstrip("/"), m.group(2)), s)
    s = re.sub(r'url\(\s*(["\']?)(/?(?:images|assets|_next|media)/[^)"\']+)\1\s*\)',
               lambda m: 'url(%s/%s)' % (base, m.group(2).lstrip("/")), s)
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--cdn", default=None, help="absolute base URL for relative asset paths")
    ap.add_argument("--fonts-css", default=None,
                    help="CSS file whose @import/@font-face replace stripped base64 fonts "
                         "(default: <page-dir>/ghl-fonts.css if it exists)")
    ap.add_argument("--keep-base64-fonts", action="store_true",
                    help="leave base64 @font-face inline (will likely blow GHL's budget)")
    ap.add_argument("--slug", default=None)
    a = ap.parse_args()

    src = pathlib.Path(a.page).resolve()  # resolve so .parent.name works for relative paths
    html = src.read_text(encoding="utf-8", errors="replace")
    # NEVER default the slug to the swipe folder name — that folder is the *reference*
    # brand, and the deliverable must carry zero trace of it. Use a neutral default;
    # pass --slug for a nicer id (e.g. the OUR-brand/offer code).
    slug = a.slug or "page"

    css_blocks, no_style = split_blocks(html, "style")
    js_blocks, no_js = split_blocks(no_style, "script")
    body = body_inner(no_js)

    css = "\n".join(css_blocks)
    js = "\n".join(js_blocks)
    if a.cdn:
        body, css = cdnify(body, a.cdn), cdnify(css, a.cdn)

    stripped = 0
    if not a.keep_base64_fonts:
        css, stripped = strip_base64_fontfaces(css)

    fonts_path = pathlib.Path(a.fonts_css) if a.fonts_css else (src.parent / "ghl-fonts.css")
    fonts_css = ""
    if fonts_path.exists():
        fonts_css = re.sub(r'(?s)/\*.*?\*/', '', fonts_path.read_text(encoding="utf-8")).strip()

    # @import must precede every other rule. Hoist all @imports (from the fonts file and
    # the page) to the very top, then FULLBLEED, then the fonts file's @font-face, then css.
    combined = (fonts_css + "\n" + css) if fonts_css else css
    imports = IMPORT_RE.findall(combined)
    rest = IMPORT_RE.sub("", combined)
    css = "".join(i + "\n" for i in imports) + FULLBLEED + "\n" + rest

    all_in_one = ('<style id="ats-%s-css">\n%s\n</style>\n<div class="ghl-swipe-root">\n%s\n</div>\n'
                  % (slug, css, body))
    tracking = "<script>\n%s\n%s\n</script>\n" % (SHIM, js)

    out = src.parent / "ghl"
    out.mkdir(exist_ok=True)
    (out / "page-html-all-in-one.html").write_text(all_in_one, encoding="utf-8")
    (out / "page-tracking.html").write_text(tracking, encoding="utf-8")
    (out / "page-html.html").write_text('<div class="ghl-swipe-root">\n%s\n</div>\n' % body, encoding="utf-8")
    (out / "page-css.css").write_text(css, encoding="utf-8")

    kb = (out / "page-html-all-in-one.html").stat().st_size // 1024
    print(f"GHL package -> {out}/  (all-in-one {kb} KB · {len(css_blocks)} style block(s) inlined · "
          f"{len(js_blocks)} script block(s) -> footer)")
    if stripped:
        where = f"replaced via {fonts_path.name}" if fonts_css else "NO fonts-css provided"
        print(f"  fonts: stripped {stripped} base64 @font-face · {len(imports)} @import hoisted · {where}")
    if stripped and not fonts_css:
        print("  WARN: base64 fonts stripped but no ghl-fonts.css — typography will fall back. "
              "Create <page-dir>/ghl-fonts.css with the page's @import.")
    if "base64," in all_in_one:
        print("  WARN: base64 data: URIs remain (images) — replace with CDN URLs; "
              "they blow GHL's ~85-100KB element budget.")
    if kb > 100:
        print(f"  WARN: all-in-one is {kb} KB (> ~100KB GHL budget) — move images/fonts to a CDN.")

if __name__ == "__main__":
    raise SystemExit(main())
