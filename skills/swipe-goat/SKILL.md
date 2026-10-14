---
name: swipe-goat
description: Use when the operator sends a funnel/landing/PDP URL and says "swipe this" (optionally "swipe this for <brand>") - captures the page as a fully self-contained single file, gates the capture, scaffolds the swipe folder, then runs the canonical swipe runbook. Also use for "activate the swipe" on a reference already on disk.
---

# swipe-goat

`_system/RUNBOOK.md` is the doctrine and the only source of truth for what a swipe
is. This skill is the front door to it: it turns a URL into a gated reference
capture and a scaffolded folder, which is the one step the runbook could not do
for itself.

Read `_system/RUNBOOK.md` in full before step 1. Do not summarise it from here.

**`$ROOT`** is the nearest ancestor of the working directory that holds `_system/`
(a workspace with its own engine wins). If there is none, `$ROOT` is
`${CLAUDE_PLUGIN_ROOT}`: the plugin ships the whole engine, so a fresh install with
nothing but a `<brand>/brand_info/brand.md` can run a swipe end to end. Every
`$ROOT/_system/...` below resolves that way.

## What a swipe is, and when it is done

**The goal is the page: the same functionality, and the same psychological
essence and impact.** Not a pixel copy, and not a rebuild from notes. The thing
being carried over is why the page converts:

- the **section order**, which is the sequence of objections it answers;
- where the **proof** sits relative to the ask;
- the **price framing** (compare-at, save badge, the add-ons beside the price);
- the **micro-commitment before the ask** (a preview generated before add-to-cart
  is the whole mechanic on a personalised PDP, not decoration);
- the **mechanics actually working**: add-ons that bill, accordions that open,
  widgets that do their job.

A page that looks identical and does nothing is a failed swipe. So is one whose
sections got reordered "to flow better". Keep the structure 1:1 and make the
mechanics real.

**It is done when:** the audit passes with `--forbid` clean and `--reference reference.html`, `layout.py` passes at phone and desktop size with popups open, `motion.py --compare` shows nothing lost, the page carries the
brand's own copy, images and links, every interaction works, and the operator has
`CONNECT.md` for their platform.

## Where the swipe stops and the operator starts

A swipe cannot reach into someone else's account, and should not try. Variant
ids, API credentials, campaign ids, pixels, the domain and the import itself are
the operator's step, with their own access.

`port.py` writes a **`CONNECT.md` into each target folder** listing exactly that
work, plus any open item the port could not resolve (an add-on with no variant
id, an unconfirmed platform assumption). Hand that over with the files. Do not
leave the connecting work implicit and do not pretend an open item is finished.

**Step 9, when the operator is ready to go live:** `_system/scripts/funnel.py`
(RUNBOOK step 9). `parse` maps the funnel and lists what tracking it lacks;
`wire` takes the operator's `wire.json` (pixel, checkout URLs, click-capture
snippet) and writes tracked pages to `wired/`. It never invents those values.

## "swipe this <url>" / "swipe this for <brand>"

```
node ${CLAUDE_PLUGIN_ROOT}/scripts/swipe-capture.mjs <url> [--brand <dir>]
```

`--brand` is the brand directory the swipe is for (e.g. `acme`, `northwind` -
whichever holds the `brand_info/` that this funnel is being rebranded into). If
the operator said "for <brand>", that is the one. If they did not, and cwd is not
already a brand dir, ask which brand before capturing - the brand decides the
folder name and every copy decision after it.

The script does step 0's mechanical half:

1. Captures with SingleFile, headless, scripts blocked. Blocked scripts are
   deliberate: a frozen static base carries none of the reference's analytics
   calls, which would be live-reference-URL leaks under hard rule 4. Step 4
   restores the JS the swipe actually needs.
2. **Runs the capture-quality gate and refuses to continue if it fails.** Zero
   external `<script src>`, zero stylesheet links, and enough visible text that
   the capture is a page rather than a bot-block shell.
3. Shoots the live page at desktop and mobile into the swipe folder, so the
   runbook's "eyeball the capture against the live page" is an actual comparison
   rather than a memory.
4. **Watches the live page for animations and popups** (`motion.py`, hard rule 7):
   phone and desktop, waits for timed popups, scrolls for scroll triggers, fires exit
   intent, and records a video. `.swipe-goat/motion/MOTION.md` lists every popup with
   its trigger and a screenshot, every animation, every carousel or ticker a script
   moves, and every countdown. The capture has already lost all of that, so this list
   is what the swipe must rebuild, and Step 6 re-runs it with `--compare` to prove it.
5. Scaffolds `SWIPE.md`, `image-manifest.json`, `DELIVERY.md`, `images/`.

Then read `MOTION.md` and pick up `_system/RUNBOOK.md` at step 0's `cp`: copy the reference to its
role name (`index.html`, `advertorial.html`, `vsl.html`) and **edit it in place**.
Never rebuild. A glitchy capture is a capture problem, and the gate exists so it
gets fixed at step 0 instead of becoming an excuse at step 4.

**Two things the capture freezes, both of which waste an afternoon:**

**Inline state.** Anything collapsed or hidden at capture time comes back with
`style="display:none"` baked on, and inline beats every stylesheet rule. Six
accordion panels on the pillow swipe were frozen shut this way: correct markup,
correct new CSS, panels still measuring 0px. Strip the frozen `display:none`
before styling. Same for a drawer, a tooltip, a second tab.

**Collapsed content is simply absent.** The panels themselves come back empty,
because the capture takes the DOM as it stands. The reader capture
(`capture.mjs`) expands accordions, so its `copy.md` is where that wording
actually is.

Prefer rebuilding these as native `<details>`/`<summary>` rather than restoring
the reference's JS: it needs no script, survives the Shopify port where JS moves
to an asset, and is keyboard accessible for free. The same logic applies to
custom checkboxes, which already hold their own state and usually only need a
`:checked` rule the capture did not carry.

**Delete SingleFile's CSP meta first.** Every capture carries
`<meta http-equiv="content-security-policy" content="default-src 'none'; ...">`
so the archive cannot phone home. On a deliverable it blocks every image you
repoint at the brand's own CDN, and it fails silently: correct markup, URL 200s,
image never paints.

## The last fork: which platform

A swipe is platform-neutral until the end. One self-contained `index.html`, then
**ask which platform it ships on** and port it:

```
python3 $ROOT/_system/scripts/port.py index.html --target ghl|shopify|checkoutchamps|all
```

| target | what it emits | why it differs |
|---|---|---|
| `ghl` | `ghl/`, four files | a Custom HTML element keeps `<style>` but strips `<script>`; the tracking footer strips `<link rel=stylesheet>`. ~85-100 KB budget. |
| `shopify` | `shopify/sections/<slug>.liquid` + `assets/` | a section is parsed as Liquid **before** it is HTML, so a literal `{{` in the swiped markup fails the theme push. Also rewires the buybox, see below. |
| `checkoutchamps` | standalone `index.html` + `assets/` | it serves whole pages. You may add JS but cannot edit its core `index.js`. The rest of that porter is unconfirmed; verify on the first real port. |
| `all` | all three | when the same offer runs on more than one platform. |

Ask rather than assume. If the operator said "swipe this for GHL" or named a
platform, that is the answer; otherwise ask before packaging, not after.

### Parity means the mechanics, not just the look

A reference page's working parts are usually rented apps. **Every one gets
rebuilt natively, replaced with ours, or explicitly dropped with the operator's
agreement. None get silently skipped.**

```
python3 $ROOT/_system/scripts/mechanics.py reference.html [rendered.html]
```

Writes `MECHANICS.md`: each app found, what it does for the visitor, what
rebuilding it takes.

**Feed it both captures.** A single-file capture has the scripts stripped, so the
`<script src>` that names the vendor is gone. On the pillow swipe the reference
alone surfaced 8 mechanics; with the reader's `rendered.html` it surfaced 12, and
the three it added (the ESP, the product personalizer, back-in-stock) were
invisible in the file we were building on.

The porter rebuilds the paid add-ons (the Candy Rack job) natively. The rest are
real builds, the personalisation/preview widget above all: on a personalised PDP
the preview generated **before** add-to-cart is the conversion mechanic, not
decoration. Price it, do not skip it.

### What cannot be swiped

**Proof.** Review counts, star averages, "40,000+ customers", shop medals and
named testimonials are claims about the reference's business. Carrying them over
puts a fabricated testimonial on the operator's store, and it is also the one
part of the page a swipe cannot supply. Structure, copy and mechanics transfer;
accumulated social proof does not.

Say so when setting expectations. Matching the page matches the mechanics, not
the trust behind them, and that gap is usually the largest one left.

**So the proof slots get the brand's real proof, or they wait for it.** Not a
bracket, not an empty logo box, not a deleted section. A swipe that shipped
`[X,XXX]+ VERIFIED REVIEWS`, `"[Press quote goes here.]"`, blank retailer logos
and no reviews carousel looked unfinished on the first scroll. Keep the section
as designed, mark the claim `[NEEDS SOURCE]` in `CROSSREF.md`, and ask the
operator for the real numbers, quotes and logos before handoff.
`audit.py --reference` fails all of those.

### Shopify: the buybox is decoration until it is wired

A swiped PDP does not sell. The price is literal text, `Add to cart` is a
`type=button` with no form around it, the quantity input has no `name`. It looks
finished and takes no orders, and nothing about it looks wrong.

The shopify target rewires it automatically: `{% form 'product', product %}`
around the smallest ancestor holding the control, price and quantity, plus the
hidden variant id, a named quantity, `type=submit name=add`, and
`{{ product.price | money }}` in place of the reference's hard-coded price.

- It matches the parts by class heuristics and **prints what each one matched**.
  Read those lines. Override with `--atc` / `--price` / `--compare` / `--qty` as
  CSS selectors, or skip with `--no-buybox`.
- No add-to-cart control found means it prints `NOT wired` and changes nothing.
  It never emits a quietly dead buybox.
- **Paid add-ons are rebuilt natively, no app.** Each add-on gets its own
  variant and the form posts the main item plus every checked add-on as line
  items in one `/cart/add.js` call. Create a variant per add-on, then re-run with
  `--addon-variant <id>` once per toggle in page order. Without ids the porter
  prints `ADD-ONS NOT BILLABLE YET` and the toggles stay inert: it takes the
  order without the add-on rather than charging nothing for it.
- Add-ons post at **quantity 1**, not the main quantity, because a per-order
  add-on billed twice is a chargeback. Set `data-addon-qty="match"` for a
  genuinely per-item one. Any failure falls back to the plain form post.
- **Place a test order on a preview theme before handing it over.** Whether the
  form actually posts is the one thing no audit here can check.

## When the gate fails

It fails loudly on purpose, and both failures have the same fix: capture it
yourself with the SingleFile browser extension in your own signed-in Chrome and
drop the file in the swipe folder, then run "activate the swipe". Pages behind a
login and pages that hard-block headless cannot be captured any other way. A
failed gate is never a licence to rebuild.

## The other job: reading a page you are going to rebuild

```
node ${CLAUDE_PLUGIN_ROOT}/scripts/capture.mjs <url> <outdir>
```

Writes `outline.json` (section order), `tokens.json` (type ramp, palette,
per-section padding), `copy.md`, `assets.json`, `rendered.html`, and both
screenshots. This is a **reader**, not a swipe base - its output still points at
external scripts and would fail the gate above.

Use it when the page is a competitor in **our own** market on **our own** product,
where the deliverable has to be our build rather than a rebranded copy of theirs.
Port the numbers and learn what job each section does; write the copy in our
voice. The swipe pipeline above is for cloning a reference funnel into a client's
brand, which is a different arrangement with a different deliverable.

## Gotchas

- A heavy funnel takes 60-90s to capture. That is SingleFile inlining every asset.
- The capture inlines images as base64, which hard rule 2 forbids in the
  deliverable. `_system/scripts/externalize_images.py` is the fix, at step 1.
- Visiting a tracked link marks that lead as engaged on their side. Capture the
  plain URL, not the one out of an SMS, unless the tracking is the thing studied.
- `capture.mjs` never clicks add to cart / buy / checkout / subscribe / submit.
  Keep it that way; a capture should never transact.
