import subprocess, sys, pathlib, tempfile, re

ROOT = pathlib.Path(__file__).resolve().parents[1]  # _system/
AUDIT = ROOT / "scripts" / "audit.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures"

def run(path, *args):
    return subprocess.run([sys.executable, str(AUDIT), str(path), *args],
                          capture_output=True, text=True)

def page(html):
    """Write html to a throwaway dir and return the path."""
    d = pathlib.Path(tempfile.mkdtemp())
    f = d / "index.html"
    f.write_text(html)
    return f

def test_bad_html_fails():
    r = run(FIX / "audit_bad.html")
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "button" in out.lower()
    assert "base64" in out.lower()

def test_good_html_passes():
    r = run(FIX / "audit_good" / "index.html")
    assert r.returncode == 0, r.stdout + r.stderr

def test_hidden_live_urls_fail():
    # Rule 4: live competitor URLs hiding in JSON-LD, og:image, <form action>,
    # srcset, and favicon must all be caught (no <button>/base64 in this fixture).
    r = run(FIX / "audit_leaks.html")
    assert r.returncode != 0, r.stdout + r.stderr
    out = (r.stdout + r.stderr).lower()
    for needle in ("json-ld", "form action", "og/twitter", "srcset", "link href"):
        assert needle in out, f"audit missed: {needle}\n{out}"

def test_forbid_catches_token_glued_into_a_word():
    # Hard rule 6 is the one that gets a client angry, and the brand token never
    # survives as a tidy standalone word — it survives as zenblueprint, zenHero,
    # zen_logo, zencdn. A word-boundary match passed all four.
    p = page('<html><body><div id="zenHero" class="zenblueprint-wrap">'
             '<img src="images/zen_logo.png"></div></body></html>')
    r = run(p, "--forbid", "zen")
    assert r.returncode != 0, r.stdout + r.stderr
    out = (r.stdout + r.stderr).lower()
    for needle in ("zenhero", "zenblueprint-wrap", "zen_logo"):
        assert needle in out, f"--forbid missed: {needle}\n{out}"

def test_forbid_ignores_base64_payloads():
    # Three random letters land inside an inlined font by chance; forbidding "zen"
    # hit 37 of them on a real deliverable and failed a clean page.
    blob = "d09GMgABAAAAAzenAA" * 40
    p = page(f'<html><head><style>@font-face{{src:url(data:font/woff2;base64,{blob})}}'
             '</style></head><body><h1>Clean</h1></body></html>')
    r = run(p, "--forbid", "zen")
    assert r.returncode == 0, r.stdout + r.stderr

def test_forbid_passes_a_clean_page():
    r = run(page("<html><body><h1>Clean</h1></body></html>"), "--forbid", "zen")
    assert r.returncode == 0, r.stdout + r.stderr

def test_allow_lets_the_clients_own_links_through():
    # A delivered swipe failed this gate on its client's own privacy-policy link,
    # which is the client's own link and exactly what should ship.
    p = page('<html><body><a href="https://go.example-client.com/privacy-policy">'
             'Privacy</a></body></html>')
    assert run(p).returncode != 0, "an undeclared live host must still fail"
    r = run(p, "--allow", "go.example-client.com")
    assert r.returncode == 0, r.stdout + r.stderr

# --- port.py ---------------------------------------------------------------

PORT = ROOT / "scripts" / "port.py"

SAMPLE = """<!doctype html><html><head><style>.a{color:#111}</style></head>
<body><div class="hero"><h1>Hi</h1></div><script>var x={{notliquid}};</script></body></html>"""

def port(target, *args):
    p = page(SAMPLE)
    r = subprocess.run([sys.executable, str(PORT), str(p), "--target", target, "--slug", "s", *args],
                       capture_output=True, text=True)
    return p.parent, r

def test_port_ghl_matches_the_production_exporter():
    # port.py re-emits the GHL package rather than calling ghl_export's main, so
    # the two can drift. They were byte-identical on a real 2.4MB deliverable when
    # this was written; this keeps them that way.
    d, r = port("ghl")
    assert r.returncode == 0, r.stdout + r.stderr
    src = d / "index.html"
    ref = pathlib.Path(tempfile.mkdtemp()) / "index.html"
    ref.write_text(src.read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "ghl_export.py"), str(ref), "--slug", "s"],
                   capture_output=True, text=True, check=True)
    for name in ("page-html-all-in-one.html", "page-tracking.html", "page-html.html", "page-css.css"):
        a = (d / "ghl" / name).read_text()
        b = (ref.parent / "ghl" / name).read_text()
        assert a == b, f"port.py and ghl_export.py disagree on {name}"

def test_port_shopify_escapes_liquid_delimiters():
    # A section is parsed as Liquid before it is HTML, so a literal {{ anywhere in
    # the body fails the theme push. Inlined widget JS is full of them.
    d, r = port("shopify")
    assert r.returncode == 0, r.stdout + r.stderr
    sec = (d / "shopify" / "sections" / "s.liquid").read_text()
    body, _, schema = sec.partition("{% schema %}")
    import json
    json.loads(schema.replace("{% endschema %}", ""))      # schema must be valid JSON
    assert "asset_url" in body                              # css/js wired as assets

def test_port_all_emits_three_targets():
    d, r = port("all")
    assert r.returncode == 0, r.stdout + r.stderr
    for sub in ("ghl", "shopify", "checkoutchamps"):
        assert (d / sub).is_dir(), f"missing {sub}: {r.stdout}"

BUYBOX = """<!doctype html><html><head><style>.a{color:#111}</style></head><body>
<div class="pdp">
  <div data-tpl="{{ handlebars }}">a widget left a literal brace here</div>
  <div class="pdp__buybox">
    <span class="pdp__price">$39.98</span>
    <span class="pdp__compare-price">$44.99</span>
    <div class="pdp__quantity"><input value="1"></div>
    <label><input type="checkbox"><strong>Rush my order</strong> get it sooner, costs more</label>
    <button class="pdp__add-button" type="button">Add to cart</button>
  </div>
</div></body></html>"""

def port_html(html, target, *args):
    d = pathlib.Path(tempfile.mkdtemp())
    f = d / "index.html"; f.write_text(html)
    r = subprocess.run([sys.executable, str(PORT), str(f), "--target", target, "--slug", "s", *args],
                       capture_output=True, text=True)
    return d, r

def test_port_shopify_wires_the_buybox():
    # A swiped buybox is decoration: literal price text, a type=button with no form,
    # an unnamed quantity input. It looks like it sells and posts nothing.
    d, r = port_html(BUYBOX, "shopify")
    assert r.returncode == 0, r.stdout + r.stderr
    sec = (d / "shopify" / "sections" / "s.liquid").read_text()
    assert "{%- form 'product', product -%}" in sec
    assert "{%- endform -%}" in sec
    assert re.search(r'<input[^>]*name="id"[^>]*product\.selected_or_first_available_variant\.id', sec), sec[:400]
    assert re.search(r'<button[^>]*name="add"', sec)
    assert re.search(r'type="submit"', sec)
    assert 'name="quantity"' in sec
    assert "{{ product.price | money }}" in sec
    assert "{{ product.compare_at_price | money }}" in sec
    assert 'name="properties[Rush my order]"' in sec

def test_port_shopify_keeps_injected_liquid_outside_raw():
    # The reference markup carries a literal {{ so the body gets {% raw %}-wrapped.
    # If the wrap swallows the injected form, the section renders Liquid as text:
    # a buybox that looks wired and takes no orders.
    d, r = port_html(BUYBOX, "shopify")
    sec = (d / "shopify" / "sections" / "s.liquid").read_text()
    assert "{%- raw -%}" in sec, "the literal {{ in the reference should have forced a raw wrap"
    i = sec.find("{%- form 'product'")
    assert i > 0
    assert sec.rfind("{%- raw -%}", 0, i) < sec.rfind("{%- endraw -%}", 0, i), \
        "the product form ended up INSIDE a {% raw %} region"
    assert "\x01" not in sec and "\x02" not in sec, "sentinels leaked into the output"

def test_port_shopify_says_so_when_the_buybox_cannot_be_wired():
    d, r = port_html("<html><body><h1>no buybox here</h1></body></html>", "shopify")
    assert r.returncode == 0
    assert "NOT wired" in r.stdout, r.stdout

def test_port_other_targets_strip_sentinels():
    for target in ("ghl", "checkoutchamps"):
        d, r = port_html(BUYBOX, target)
        blob = "".join(f.read_text() for f in (d / target).rglob("*") if f.is_file())
        assert "\x01" not in blob and "\x02" not in blob, f"{target} leaked sentinels"

def test_addons_are_not_billable_until_variant_ids_are_given():
    # Line-item properties record an add-on and charge nothing for it. Shipping
    # that silently gives the upsell away, so the porter has to say so loudly.
    d, r = port_html(BUYBOX, "shopify")
    assert "ADD-ONS NOT BILLABLE YET" in r.stdout, r.stdout
    sec = (d / "shopify" / "sections" / "s.liquid").read_text()
    assert 'data-addon-variant="REPLACE_WITH_VARIANT_ID"' in sec

def test_addons_wire_to_their_own_line_items():
    d, r = port_html(BUYBOX, "shopify", "--addon-variant", "900002")
    assert "NOT BILLABLE" not in r.stdout, r.stdout
    sec = (d / "shopify" / "sections" / "s.liquid").read_text()
    assert 'data-addon-variant="900002"' in sec
    js = (d / "shopify" / "assets" / "s.js").read_text()
    assert "/cart/add.js" in js, "the multi-item add script should ship with the section"
    assert "form.submit()" in js, "there must be a fallback to the plain post"

def test_addon_script_only_ships_when_there_are_addons():
    plain = BUYBOX.replace('<label><input type="checkbox"><strong>Rush my order</strong> get it sooner, costs more</label>', '')
    d, r = port_html(plain, "shopify")
    js = (d / "shopify" / "assets" / "s.js").read_text()
    assert "/cart/add.js" not in js, "no add-ons on the page, so no add-on script"

def test_every_target_writes_a_connect_doc():
    # The connecting work is the operator's, with their own access. Leaving it
    # implicit is how a finished swipe sits unused.
    d, r = port_html(BUYBOX, "all")
    for target, needle in (("ghl", "Tracking Code"), ("shopify", "unpublished preview theme"),
                           ("checkoutchamps", "index.js")):
        doc = (d / target / "CONNECT.md")
        assert doc.exists(), f"{target} has no CONNECT.md"
        assert needle in doc.read_text(), f"{target} CONNECT.md missing {needle!r}"

def test_connect_doc_carries_unresolved_items():
    d, r = port_html(BUYBOX, "shopify")
    doc = (d / "shopify" / "CONNECT.md").read_text()
    assert "Open items" in doc and "NOT BILLABLE" in doc, doc

MECH = ROOT / "scripts" / "mechanics.py"

def test_mechanics_finds_rented_apps_and_writes_the_build_list():
    p = page('<html><body><div data-uploadly-embed="true"></div>'
             '<script src="https://candyrack.ds-cdn.com/a.js"></script>'
             '<div class="jdgm-widget"></div>'
             '<a href="https://af.uppromote.com/x/register">join</a>'
             '<div data-madeup-embed="1"></div></body></html>')
    r = subprocess.run([sys.executable, str(MECH), str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = (p.parent / "MECHANICS.md").read_text()
    for vendor in ("Uploadly", "Candy Rack", "Judge.me", "affiliate app"):
        assert vendor in doc, f"{vendor} not reported\n{doc}"
    # an embed hook with no known vendor still has to be surfaced, not ignored
    assert "data-madeup-*" in doc, doc

def test_visible_placeholders_and_dead_images_fail():
    # A real swipe shipped these with every other gate green.
    r = run(page('<p>[X,XXX]+ verified reviews</p><blockquote>"[Press quote goes here.]"</blockquote>'
                 '<p>note<sup>[1]</sup></p><img src="https://example.com/logo.png"><img src="">'))
    out = r.stdout
    assert r.returncode != 0
    assert "[X,XXX]" in out and "[Press quote goes here.]" in out
    assert "[1]" not in out
    assert out.count("no real source") == 2

def test_dropped_section_or_video_fails_against_reference():
    ref = page('<section>a</section><section>reviews</section><video></video>')
    ours = page('<section>a</section><img src="images/x.jpg">')
    (ours.parent / "images").mkdir()
    (ours.parent / "images" / "x.jpg").write_text("x")
    r = run(ours, "--reference", str(ref))
    assert r.returncode != 0
    assert "sections: reference has 2" in r.stdout and "videos: reference has 1" in r.stdout
    assert run(ours).returncode == 0, "without --reference the count is not checked"

if __name__ == "__main__":
    # Runnable without pytest: pytest is not installed on the machine this ships
    # to, and a suite that needs a setup step is a suite nobody runs.
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"ok   {name}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
    print(f"\n{fails} failed")
    raise SystemExit(1 if fails else 0)
