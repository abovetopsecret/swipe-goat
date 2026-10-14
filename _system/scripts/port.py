#!/usr/bin/env python3
"""Port a finished swipe (standalone index.html) to a target platform.

The swipe itself is platform-neutral: one self-contained index.html. Where it
goes is the last fork, and each platform wants a different shape.

  ghl             GoHighLevel Custom-HTML package (style inline, JS to the footer)
  shopify         a theme section + assets, Liquid-safe
  checkoutchamps  a standalone page with external css/js
  all             all three, side by side

Usage:
  python3 port.py <page.html> --target ghl|shopify|checkoutchamps|all
                  [--cdn https://assets.brand.com] [--slug NAME]
                  [--fonts-css ghl-fonts.css] [--keep-base64-fonts]

Why each shape differs:

  GHL     a Custom HTML element keeps <style> but strips <script>, and the
          tracking footer strips <link rel=stylesheet>. So: CSS inline in the
          element, all JS in the footer, nothing external. ~85-100KB budget.

  Shopify a section is Liquid, and Liquid parses the file before it is HTML.
          Any literal {{ or {% in the swiped markup (common inside inlined JS)
          is a syntax error at theme push, so the body is wrapped in {% raw %}.
          CSS and JS go to assets/ because a section has no budget problem and
          the theme editor is happier with small section files.

  CC      Checkout Champ serves whole pages, so the standalone file is close to
          what it wants. Its one documented limit is that you may add your own
          JS but cannot edit the core index.js, so nothing here may assume it
          can override platform behaviour. CONFIRM the rest on the first real
          port and correct this note; it is the least documented of the three.
"""
import argparse, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ghl_export import (FULLBLEED, SHIM, IMPORT_RE, split_blocks, body_inner,
                        cdnify, strip_base64_fontfaces)


def prepare(src, a):
    """The half every target shares: split the file, resolve fonts, hoist imports."""
    html = src.read_text(encoding="utf-8", errors="replace")
    css_blocks, no_style = split_blocks(html, "style")
    js_blocks, no_js = split_blocks(no_style, "script")
    body = body_inner(no_js)
    css, js = "\n".join(css_blocks), "\n".join(js_blocks)

    if a.cdn:
        body, css = cdnify(body, a.cdn), cdnify(css, a.cdn)

    stripped = 0
    if not a.keep_base64_fonts:
        css, stripped = strip_base64_fontfaces(css)

    fonts_path = pathlib.Path(a.fonts_css) if a.fonts_css else (src.parent / "ghl-fonts.css")
    fonts_css = ""
    if fonts_path.exists():
        fonts_css = re.sub(r'(?s)/\*.*?\*/', '', fonts_path.read_text(encoding="utf-8")).strip()

    combined = (fonts_css + "\n" + css) if fonts_css else css
    imports = IMPORT_RE.findall(combined)
    css = "".join(i + "\n" for i in imports) + IMPORT_RE.sub("", combined)
    return body, css, js, stripped, len(css_blocks), len(js_blocks)


# --- handoff ---------------------------------------------------------------

# The swipe's job is the page: same function, same psychological shape. What it
# cannot do is reach into someone else's account. Variant ids, API credentials,
# campaign ids, pixels and the import itself are the operator's step, and a
# handoff that leaves them implicit is how a finished swipe sits unused for a
# week. Each target writes its own CONNECT.md so the remaining work is a list,
# not a conversation.
CONNECT = {
"ghl": """# Connect: GoHighLevel

1. **Custom HTML element** -> paste `page-html-all-in-one.html`. It carries the CSS;
   it must contain no `<script>`.
2. **Page Settings -> Tracking Code -> Footer** -> paste `page-tracking.html`. All the
   page JS lives here, plus the ancestor-padding shim.
3. **Host the images and fonts on your CDN**, then re-run with `--cdn https://...`.
   Base64 assets blow the ~85-100 KB element budget.
4. **Point the lead form at your endpoint** and confirm the webhook payload and
   SMS consent wording before the first send.
5. Preview on desktop and mobile in GHL itself. The builder's wrapper is not the
   same as a local file.
""",
"shopify": """# Connect: Shopify

1. **Theme files** -> `sections/<slug>.liquid` into `sections/`, `assets/*` into
   `assets/`. Push to an **unpublished preview theme**, never the live one.
2. **Product** -> the section reads `product`, so assign it through a product
   template (`templates/product.<name>.json`) on the product this page sells.
3. **Add-ons** -> create a product/variant per upsell at its real price, then
   re-run with `--addon-variant <id>` once per toggle, in page order. Until then
   the toggles are inert by design.
4. **Place a test order end to end**, including a checked add-on. Whether the cart
   takes it is the one thing nothing here can prove.
5. **Images** -> replace the remaining base64 with theme assets or your CDN.
6. Reviews and any photo/preview widget need your own app or build; the page
   leaves the slots in place.
""",
"checkoutchamps": """# Connect: Checkout Champ

1. **Upload** `index.html` plus `assets/`.
2. **Order form** -> map the fields to the campaign and product ids in your account.
   The swiped form is markup; it does not know your campaign.
3. **Do not edit the core `index.js`.** Add your own JS as a separate include; the
   platform owns that file.
4. **Confirm the upload shape on this first port.** Whether CC wants a single file,
   a bundle or relative assets is the least documented part of this porter: if it
   differs, fix `port_checkoutchamps` so the next one is right.
""",
}


def write_connect(out, target, notes):
    doc = CONNECT[target]
    open_items = [n for n in notes if n.isupper() or "NOT " in n or "CONFIRM" in n]
    if open_items:
        doc += "\n## Open items from this port\n\n" + "".join("- %s\n" % n for n in open_items)
    (out / "CONNECT.md").write_text(doc, encoding="utf-8")


def port_ghl(src, body, css, js, slug):
    body = body.replace("\x01", "").replace("\x02", "")
    out = src.parent / "ghl"; out.mkdir(exist_ok=True)
    css = re.sub(r'^((?:@import[^\n]*\n)*)', r'\1' + FULLBLEED + "\n", css, count=1)
    (out / "page-html-all-in-one.html").write_text(
        '<style id="ats-%s-css">\n%s\n</style>\n<div class="ghl-swipe-root">\n%s\n</div>\n' % (slug, css, body),
        encoding="utf-8")
    (out / "page-tracking.html").write_text("<script>\n%s\n%s\n</script>\n" % (SHIM, js), encoding="utf-8")
    (out / "page-html.html").write_text('<div class="ghl-swipe-root">\n%s\n</div>\n' % body, encoding="utf-8")
    (out / "page-css.css").write_text(css, encoding="utf-8")
    kb = (out / "page-html-all-in-one.html").stat().st_size // 1024
    notes = []
    if kb > 100:
        notes.append(f"all-in-one is {kb} KB, over GHL's ~100KB element budget: move images and fonts to a CDN")
    return out, f"all-in-one {kb} KB", notes


# --- shopify buybox --------------------------------------------------------

# A swiped PDP's buybox is decoration: the price is literal text, "Add to cart"
# is a type=button with no form around it, and the quantity input has no name.
# It looks like it sells and it cannot. Shopify needs a real product form, so
# this finds the parts and rewires them, and says loudly what it could not find
# rather than emitting a page that looks finished and takes no orders.
BUYBOX_HINTS = {
    "atc":     ['[class*="add-button"]', '[class*="add-to-cart"]', '[class*="addtocart"]'],
    "price":   ['[class*="__price"]', '[class*="product-price"]', '[class*="price-item--regular"]'],
    "compare": ['[class*="compare-price"]', '[class*="compare_at"]', '[class*="price-item--sale"]'],
    "qty":     ['[class*="quantity"] input', 'input[name*="quantity"]', 'input[type="number"]'],
}
# Injected Liquid is marked so the {% raw %} wrap below can step around it.
# Without this the wrap swallows the product form and the section renders the
# Liquid as literal text: a buybox that looks wired and posts nothing.
LIQ_OPEN, LIQ_SHUT = "\x01", "\x02"

ATC_TEXT = re.compile(r"^\s*(add to cart|add to bag|buy now|get (my|yours)\b.*)\s*$", re.I)


def _find(soup, kind, override):
    if override:
        el = soup.select_one(override)
        return el, ("--%s %s" % (kind, override) if el else None)
    for sel in BUYBOX_HINTS[kind]:
        # Innermost match only. '[class*="__price"]' also matches the price ROW,
        # and wiring the row overwrote the compare-at price and the save badge
        # inside it with the bare product.price.
        hits = soup.select(sel)
        el = next((h for h in hits if not h.select_one(sel)), None)
        if el:
            return el, sel
    if kind == "atc":
        for el in soup.find_all(["button", "a"]):
            if ATC_TEXT.match(el.get_text(" ", strip=True) or ""):
                return el, "text match"
    return None, None


def wire_shopify_buybox(body, opts):
    """Return (body, notes). Rewires the static buybox into a Shopify product form."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return body, ["buybox NOT wired: beautifulsoup4 is not installed (pip install beautifulsoup4 lxml)"]

    soup = BeautifulSoup(body, "html.parser")
    notes, found = [], {}
    for kind in ("atc", "price", "compare", "qty"):
        found[kind], how = _find(soup, kind, getattr(opts, kind, None))
        if found[kind]:
            notes.append(f"buybox {kind}: matched {how}")

    atc = found["atc"]
    if atc is None:
        return body, ["buybox NOT wired: no add-to-cart control found. "
                      "Pass --atc '<css selector>' and re-run; the section will not sell until this is wired."]

    # The form has to enclose every field it posts, so wrap the smallest ancestor
    # that contains the control AND the quantity, not just the button.
    container = atc
    needed = [e for e in (found["qty"], found["price"]) if e is not None]
    while container.parent is not None and container.parent.name not in ("[document]", "body"):
        if all(n in container.descendants for n in needed):
            break
        container = container.parent

    atc.name = "button"
    atc["type"] = "submit"
    atc["name"] = "add"

    if found["qty"] is not None:
        found["qty"]["name"] = "quantity"
        if "min" not in found["qty"].attrs:
            found["qty"]["min"] = "1"
    else:
        notes.append("buybox qty: not found, posting quantity 1 (pass --qty to wire the stepper)")

    if found["price"] is not None:
        found["price"].string = LIQ_OPEN + "{{ product.price | money }}" + LIQ_SHUT
    else:
        notes.append("buybox price: not found, the page will show the reference's hard-coded price "
                     "(pass --price to wire it)")
    if found["compare"] is not None:
        found["compare"].string = LIQ_OPEN + "{{ product.compare_at_price | money }}" + LIQ_SHUT

    # Line-item properties record an add-on choice but do NOT charge for it.
    boxes = soup.select('input[type="checkbox"]')
    for box in boxes:
        # The whole label block is the headline plus its explainer paragraph, which
        # makes a 50-character property name. The headline is the <strong>.
        label = box.find_parent()
        head = label.find(["strong", "b", "label", "h4"]) if label else None
        text = (head or label).get_text(" ", strip=True) if (head or label) else "option"
        text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:40] or "option"
        box["name"] = "properties[%s]" % text
        box["value"] = "Yes"
    if boxes:
        notes.append(f"buybox upsells: {len(boxes)} checkbox(es) keep a line-item property so the "
                     "choice shows on the order")
        notes += wire_addons(soup, list(getattr(opts, "addon_variant", None) or []))

    inner = "".join(str(c) for c in container.children)
    form = (LIQ_OPEN + "{%- form 'product', product -%}"
            '<input type="hidden" name="id" value="{{ product.selected_or_first_available_variant.id }}">'
            + LIQ_SHUT + inner + LIQ_OPEN + "{%- endform -%}" + LIQ_SHUT)
    container.clear()
    container.append(BeautifulSoup(form, "html.parser"))
    notes.append("buybox wired: {% form 'product', product %} with the variant id, quantity and submit")
    return str(soup), notes


# --- native add-on upsells (the Candy Rack job, without Candy Rack) ---------

# A reference PDP's paid add-ons are almost always an app: Candy Rack, Zipify OCU,
# ReConvert. Line-item properties alone record the choice and never charge for it,
# so a swipe that stops there ships an upsell that silently gives the add-on away.
#
# The native equivalent: each add-on is its own Shopify variant, and the form posts
# the main item plus every checked add-on as line items in ONE /cart/add.js call.
# No app, no monthly fee, and it degrades to a plain form post if anything fails.
ADDON_JS = """
/* swipe-goat: native add-on upsells. Each [data-addon-variant] posts as its own
   line item. Falls back to the plain form post on any failure, because a cart
   that silently drops the main product is worse than one that skips an add-on. */
(function () {
  var form = document.querySelector('form[action*="/cart/add"]');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    var toggles = [].slice.call(form.querySelectorAll('[data-addon-variant]'));
    var chosen = toggles.filter(function (el) { return el.checked; });
    if (!chosen.length) return;                      /* nothing extra: let it post normally */

    var unset = chosen.filter(function (el) { return !/^\\d+$/.test(el.dataset.addonVariant || ''); });
    if (unset.length) {
      /* The porter could not be told the real variant ids. Posting a placeholder
         would 404 the whole add, so take the order without the add-on and say why. */
      console.warn('swipe-goat: add-on variant id not set on', unset.length, 'toggle(s); posting without them');
      return;
    }

    e.preventDefault();
    var idEl = form.querySelector('[name="id"]');
    var qtyEl = form.querySelector('[name="quantity"]');
    var qty = Math.max(1, parseInt((qtyEl && qtyEl.value) || '1', 10) || 1);
    /* Carry the form's line-item properties onto the main item. A plain form
       post sends them for free; this JSON post only sends what it is given, and
       dropping them loses whatever personalises the order (a pet's name, a
       preview id) for exactly the shoppers who paid for an add-on. */
    var props = {};
    new FormData(form).forEach(function (v, k) {
      var m = /^properties\\[(.+)\\]$/.exec(k);
      if (m && typeof v === 'string' && v !== '') props[m[1]] = v;
    });
    var items = [{ id: idEl.value, quantity: qty, properties: props }];
    chosen.forEach(function (el) {
      /* Add-ons go on at quantity 1, not the main quantity. "Rush my order" is
         per-order: billing it twice on a 2-pillow order is a chargeback waiting
         to happen, and undercharging is the cheaper mistake. For a genuinely
         per-item add-on set data-addon-qty="match" on the toggle. */
      var aq = el.dataset.addonQty === 'match' ? qty : 1;
      items.push({ id: el.dataset.addonVariant, quantity: aq });
    });

    var btn = form.querySelector('[name="add"]');
    if (btn) btn.disabled = true;
    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: items })
    }).then(function (r) {
      if (!r.ok) throw new Error('cart/add.js ' + r.status);
      window.location = '/cart';
    }).catch(function (err) {
      console.warn('swipe-goat: multi-item add failed, falling back to plain post', err);
      if (btn) btn.disabled = false;
      form.submit();
    });
  });
})();
"""


def wire_addons(soup, variants):
    """Tag each upsell checkbox with its own variant id. Returns notes."""
    boxes = soup.select('input[type="checkbox"]')
    if not boxes:
        return []
    notes = []
    for i, box in enumerate(boxes):
        box["data-addon-variant"] = variants[i] if i < len(variants) else "REPLACE_WITH_VARIANT_ID"
    missing = max(0, len(boxes) - len(variants))
    if missing:
        notes.append(f"ADD-ONS NOT BILLABLE YET: {missing} of {len(boxes)} toggle(s) have no variant id. "
                     f"Create a product/variant per add-on, then re-run with "
                     f"--addon-variant <id> once per toggle, in page order. "
                     f"Until then the page takes the order WITHOUT the add-on rather than charging nothing for it.")
    if len(variants) > len(boxes):
        notes.append(f"{len(variants)} --addon-variant given but only {len(boxes)} toggle(s) found; extras ignored")
    if variants:
        notes.append(f"add-ons: {min(len(boxes), len(variants))} toggle(s) post as their own line item via /cart/add.js")
    return notes


# Shopify caps a section file at 256 KB of "template content", and a swiped page
# carries its images inlined as base64, so a real deliverable lands around 1 MB
# and the push is refused. Images move to assets/ and the section references them
# with asset_url. Only the section is capped; the CSS asset is not, so base64
# inside the stylesheet is left alone.
DATA_URI_EXT = {
    "image/webp": "webp", "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
    "image/gif": "gif", "image/svg+xml": "svg", "image/avif": "avif",
    "image/x-icon": "ico", "image/vnd.microsoft.icon": "ico",
}


def extract_section_images(body, out, slug):
    """Write inlined images to assets/ and point the markup at asset_url.

    The asset_url tags are wrapped in the same sentinels the buybox wiring uses,
    so they survive stepping outside the {% raw %} block that guards the swiped
    markup.
    """
    seen, written = {}, []

    def swap(m):
        attr, mime, payload = m.group(1), m.group(2).lower(), m.group(3)
        ext = DATA_URI_EXT.get(mime)
        if ext is None:
            return m.group(0)
        key = hash(payload)
        if key not in seen:
            import base64, binascii
            try:
                raw = base64.b64decode(payload, validate=False)
            except (binascii.Error, ValueError):
                return m.group(0)
            if not raw:
                return m.group(0)
            name = f"{slug}-{len(seen) + 1}.{ext}"
            (out / "assets" / name).write_bytes(raw)
            seen[key] = name
            written.append((name, len(raw)))
        return f'{attr}="{LIQ_OPEN}{{{{ \'{seen[key]}\' | asset_url }}}}{LIQ_SHUT}"'

    body = re.sub(r'\b(src|href|poster)="data:([^;",]+);base64,([A-Za-z0-9+/=\s]+)"',
                  swap, body)
    return body, written


# Step 3 of the runbook leaves images as relative images/<file> paths, which a
# theme cannot serve: they would all 404. Copy them into assets/ (a flat folder,
# hence the slug prefix) and point the markup at asset_url. The CSS asset is
# served from that same folder, so its url() only needs the bare filename.
LOCAL_IMG = re.compile(r'(?<![\w/.-])images/([\w.-]+\.(?:png|jpe?g|webp|gif|svg|avif|ico))')


def extract_local_images(body, css, src, out, slug):
    copied, missing = {}, []

    def name(f):
        if f not in copied:
            p = src.parent / "images" / f
            if not p.exists():
                missing.append(f)
                return None
            copied[f] = f"{slug}-{f}"
            (out / "assets" / copied[f]).write_bytes(p.read_bytes())
        return copied[f]

    def in_body(m):
        n = name(m.group(1))
        return f"{LIQ_OPEN}{{{{ '{n}' | asset_url }}}}{LIQ_SHUT}" if n else m.group(0)

    def in_css(m):
        n = name(m.group(1))
        return n or m.group(0)

    return LOCAL_IMG.sub(in_body, body), LOCAL_IMG.sub(in_css, css), copied, missing


def port_shopify(src, body, css, js, slug, opts=None):
    out = src.parent / "shopify"
    (out / "sections").mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(parents=True, exist_ok=True)

    wire_notes = []
    if opts is None or not getattr(opts, "no_buybox", False):
        body, wire_notes = wire_shopify_buybox(body, opts)

    body, moved = extract_section_images(body, out, slug)
    body, css, local, missing = extract_local_images(body, css, src, out, slug)

    # Liquid parses the file before anything treats it as HTML, so a literal {{ or
    # {% anywhere in the SWIPED markup is a theme-push error. Inlined JS is full of
    # them. Wrap rather than hunt them down one at a time, but step around the
    # Liquid the buybox wiring injected, which is marked with sentinels.
    swiped = re.sub(r'\x01.*?\x02', '', body, flags=re.S)
    raw_needed = len(re.findall(r'\{\{|\{%', swiped))
    if raw_needed:
        safe = ("{%- raw -%}" + body + "{%- endraw -%}")
        safe = safe.replace("\x01", "{%- endraw -%}").replace("\x02", "{%- raw -%}")
    else:
        safe = body.replace("\x01", "").replace("\x02", "")

    section = (
        "{{ 'SLUG.css' | asset_url | stylesheet_tag }}\n"
        '<div class="SLUG-root">\n'
        "SAFE\n"
        "</div>\n"
        "{{ 'SLUG.js' | asset_url | script_tag }}\n\n"
        "{% schema %}\n"
        '{\n  "name": "SLUG",\n  "settings": [],\n'
        '  "presets": [{ "name": "SLUG" }]\n}\n'
        "{% endschema %}\n"
    ).replace("SLUG", slug).replace("SAFE", safe)

    (out / "sections" / f"{slug}.liquid").write_text(section, encoding="utf-8")
    (out / "assets" / f"{slug}.css").write_text(css, encoding="utf-8")
    needs_addons = "data-addon-variant" in body
    (out / "assets" / f"{slug}.js").write_text(
        (js + "\n" + ADDON_JS) if needs_addons else js, encoding="utf-8")

    notes = list(wire_notes)
    if raw_needed:
        notes.append(f"wrapped the body in {{% raw %}} ({raw_needed} literal Liquid delimiters would "
                     f"otherwise fail the theme push)")
    if moved:
        kb = sum(n for _, n in moved) // 1024
        notes.append(f"moved {len(moved)} inlined image(s) to assets/ ({kb} KB); a section file is "
                     f"capped at 256 KB and a swiped page is well over it")
    if local:
        notes.append(f"copied {len(local)} images/ file(s) to assets/ as {slug}-<name> and pointed "
                     f"the markup at asset_url")
    if missing:
        notes.append(f"IMAGES NOT FOUND: {', '.join(sorted(set(missing)))} (referenced as images/... "
                     f"but missing on disk; they will 404)")
    # One unparseable block kills every script in the file, and the page still
    # looks finished. JSON-LD glued onto the front of it did exactly that.
    import shutil, subprocess
    if shutil.which("node"):
        chk = subprocess.run(["node", "--check", str(out / "assets" / f"{slug}.js")],
                             capture_output=True, text=True)
        if chk.returncode != 0:
            err = next((l for l in chk.stderr.splitlines() if "Error" in l), "see node --check")
            notes.append(f"JS DOES NOT PARSE: assets/{slug}.js ({err}). No script on the page will run.")
    else:
        notes.append("JS NOT CHECKED: node is not installed, so assets/*.js was not parse-checked")
    size = len((out / "sections" / f"{slug}.liquid").read_text(encoding="utf-8").encode("utf-8"))
    if size > 256 * 1024:
        notes.append(f"STILL TOO BIG: section is {size // 1024} KB against Shopify's 256 KB limit. "
                     f"The push will be refused. Trim the markup or split the section.")
    if "base64," in css:
        notes.append("base64 data: URIs remain in the CSS asset; that file is not capped, so this "
                     "is fine, but moving them to assets/ keeps the stylesheet readable")
    return out, f"section + {2 + len(moved) + len(local)} assets", notes


def port_checkoutchamps(src, body, css, js, slug):
    body = body.replace("\x01", "").replace("\x02", "")
    out = src.parent / "checkoutchamps"
    (out / "assets").mkdir(parents=True, exist_ok=True)
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<link rel="stylesheet" href="assets/{slug}.css">\n</head>\n<body>\n'
        f'<div class="{slug}-root">\n{body}\n</div>\n'
        f'<script src="assets/{slug}.js"></script>\n</body>\n</html>\n'
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "assets" / f"{slug}.css").write_text(css, encoding="utf-8")
    (out / "assets" / f"{slug}.js").write_text(js, encoding="utf-8")
    notes = [
        "assumes Checkout Champ serves a whole page with relative assets; CONFIRM on the first "
        "real port and fix this porter if it wants a single file or an upload bundle",
        "its one documented limit: you may add JS but cannot edit the core index.js, so nothing "
        "here may rely on overriding platform behaviour",
    ]
    return out, "standalone page + 2 assets", notes


TARGETS = {"ghl": port_ghl, "shopify": port_shopify, "checkoutchamps": port_checkoutchamps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--target", required=True, choices=list(TARGETS) + ["all"])
    ap.add_argument("--cdn", default=None)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--fonts-css", default=None)
    ap.add_argument("--keep-base64-fonts", action="store_true")
    # shopify buybox wiring: heuristics by default, selectors to override
    ap.add_argument("--atc", default=None, help="CSS selector for the add-to-cart control")
    ap.add_argument("--price", default=None, help="CSS selector for the price node")
    ap.add_argument("--compare", default=None, help="CSS selector for the compare-at price")
    ap.add_argument("--qty", default=None, help="CSS selector for the quantity input")
    ap.add_argument("--no-buybox", action="store_true", help="skip buybox wiring")
    ap.add_argument("--addon-variant", action="append", default=[],
                    help="Shopify variant id for an upsell toggle; repeat once per toggle, "
                         "in the order they appear on the page")
    a = ap.parse_args()

    src = pathlib.Path(a.page).resolve()
    if not src.exists():
        print(f"PORT ERROR: page not found: {src}", file=sys.stderr); return 2
    # Never default the slug to the swipe folder: that folder is named for the
    # REFERENCE brand, and hard rule 6 says the deliverable carries zero trace of it.
    slug = a.slug or "page"

    body, css, js, stripped, n_css, n_js = prepare(src, a)
    print(f"{src.name}: {n_css} style block(s), {n_js} script block(s)"
          + (f", stripped {stripped} base64 @font-face" if stripped else ""))

    for name in (list(TARGETS) if a.target == "all" else [a.target]):
        fn = TARGETS[name]
        out, summary, notes = (fn(src, body, css, js, slug, a)
                               if name == 'shopify' else fn(src, body, css, js, slug))
        write_connect(out, name, notes)
        print(f"\n  {name:15} -> {out}/  ({summary} + CONNECT.md)")
        for n in notes:
            print(f"      note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
