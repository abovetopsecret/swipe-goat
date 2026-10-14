# Swipe Runbook (canonical)

The single source of truth for a **swipe**: cloning a validated reference funnel into our
brand/offer. `CLAUDE.md` (builder) and `AGENTS.md` (Codex) both point here; they differ
only at Step 3 (who makes the image pixels).

## What a swipe is
**The goal is the page: same functionality, same psychological essence and impact.**
What carries over is why it converts: the section order (which is the sequence of
objections it answers), where the proof sits relative to the ask, the price framing,
the micro-commitment before the ask, and the mechanics actually working. A page that
looks identical and does nothing is a failed swipe; so is one whose sections got
reordered "to flow better".

**Where the swipe stops:** it cannot reach into the operator's account, and should not
try. Variant ids, API credentials, campaign ids, pixels, the domain and the import are
their step. `port.py` writes a `CONNECT.md` into each target folder listing that work
plus any open item the port could not resolve. Hand it over with the files.

## Prime directive
The reference HTML is the **base and source of truth**. The deliverable is **literally a
copy of the reference file** (`cp` it to the deliverable name) that you **edit in place** —
same DOM, same CSS, same layout. **Never recreate, rebuild, re-slim, tree-shake, or
restructure it.** Keep it **1:1**: change only (a) text/copy, (b) the **brand visual
identity** — palette colors, logo, and the brand name/wordmark, (c) image `src`/`srcset`,
and (d) link targets. Minimal, high-leverage edits — if you're not deliberately swapping
copy, brand visuals, an image, or a link, leave the bytes exactly as they were. Same layout,
same components — but it must look like **our** brand, not the reference's.

**Offers are swiped 1:1 too, even when the brand has no matching offer.** Countdown
sales, gift-with-purchase popups, was/now prices, bundles, scarcity bars: keep every one
in place with the brand's name and product swapped in, and log each in `CROSSREF.md` as
`[ADJUST AFTER SWIPE]`. The operator adjusts offers after the swipe is delivered. Never
cut, soften or rewrite an offer mechanic during the swipe because the brand lacks it,
and never let a brand file's "do not imply" rules remove one: those rules apply to the
post-swipe adjustment, not to the swipe.

**If a static capture renders glitchy, that's a capture problem — not a license to rebuild.**
Get a fully self-contained capture (Step 0 capture-quality gate) and restore any frozen JS
(Step 4); never reconstruct. Reconstructing is how you inherit broken buy boxes, dead tabs,
and overflow bugs — the exact failure this prime directive exists to prevent.

## Trigger
**From a URL:** the operator sends a funnel link and says **"swipe this"** (or "swipe this
for `<brand>`"). Run `${CLAUDE_PLUGIN_ROOT}/scripts/swipe-capture.mjs <url> --brand <dir>` first (the swipe-goat plugin; it also runs `motion.py` on the live URL) — it captures
the reference self-contained, runs the Step 0 capture-quality gate, shoots the live page,
and scaffolds the folder — then start at Step 0's `cp`.

**From a file:** when the operator says **"activate the swipe"** (or "swipe" / "go") while `cd`'d in a
brand dir (e.g. `acme`, `northwind`) that contains a loose reference `*.html`, run
the steps below. The brand's truth lives in `brand_info/brand.md` (read it fully first)
and `brand_info/assets/`.

## Hard rules (non-negotiable — see `_system/checklists/coc-ghl-rules.md`)
1. No `<button>` tags — use `<a>` / styled `<div>`/`<span>`.
2. No base64 `data:` **images** — images are external files in the swipe's `images/`.
   (Fonts inlined by the capture are **exempt**: keep them as-is to preserve typography
   1:1 — never stub a font URL to a dead placeholder like `example.com/fonts/...`.)
3. No baked copy in images — all text stays live HTML.
4. No live reference-brand URLs — stub every checkout/legal/nav href + canonical/OG/
   JSON-LD to `#` or `https://example.com/...`.
5. Structure stays 1:1 — never move/add/remove sections.
6. **Zero reference-brand trace** — the deliverable (`index.html` + the whole `ghl/`
   package) must contain **no** mention of the brand it was swiped from: not in copy,
   slugs, element ids, class names, comments, JSON-LD, meta, or filenames. This is what
   "clean the code" means. Never let the swipe **folder name** (which is the reference
   brand) leak into a slug/id — always pass `ghl_export.py --slug <our-offer-code>`. The
   audit enforces it: `audit.py --forbid <ref-brand> --forbid <ref-domain>`. `--forbid`
  matches as a **substring**, so `--forbid zen` also catches `zenblueprint`, `zenHero`
  and `zen_logo`; it reports the whole word each hit sits in, so a false positive
  ("zenith") is visible and the token can be narrowed.

7. **Every animation and popup comes across.** The page is what it DOES: timed and
   exit-intent popups, scroll-triggered bars and offers, carousels, tickers, countdowns,
   counters, reveal-on-scroll, sticky bars that slide in, and every video or animated
   illustration (a still image in a video's slot is a dropped animation: the looping
   "how it works" explainer is often the page's mechanism). A capture is a snapshot, so it
   keeps CSS keyframes and loses the rest; each one is rebuilt, or dropped only with the
   operator's say-so, recorded in `CONTROLS.md`. `motion.py` lists them (Step 0b) and
   proves parity (Step 6).

Pass the client's own domain with `--allow`, or the gate fails the finished deliverable on
its legitimate privacy-policy and terms links:
`audit.py index.html --forbid <ref-brand> --allow <client-domain>`.

## Deliverable: whatever the target platform takes (default: a GHL Custom-HTML package)
A finished swipe ships as a **GoHighLevel Custom-HTML package** — the format GHL funnels
go live in. Built in Step 7
into `swipes/<name>/ghl/`:

- **`page-html-all-in-one.html`** — ✅ THE PASTE. One `<style>` block + the body wrapped in
  `<div class="ghl-swipe-root">…</div>`. Goes into a **GHL Custom HTML element**.
- **`page-tracking.html`** — all the page's JS (countdown, carousel, VSL, form submit) + an
  ancestor-padding shim. Goes into **Page Settings → Tracking Code → Footer**.
- **`index.html`** — the standalone version (raw hosting / preview / QA).

Three GHL behaviors force this split (don't fight them):
- A Custom HTML element **keeps `<style>` but strips `<script>`** → CSS inline in the
  element, **all JS in the tracking footer**.
- The tracking footer **strips `<link rel=stylesheet>`** → never rely on external CSS links.
- Page Settings → Custom CSS is unreliable → bundle CSS into the all-in-one, not there.

Package rules:
- **No `<script>` in the all-in-one** — JS lives only in `page-tracking.html`.
- **Images + fonts via absolute CDN URLs** (host on the brand's domain). Base64 blows the
  all-in-one's ~85–100 KB budget — fine for the standalone `index.html`, not for GHL.
- **Full-bleed wrapper:** `.ghl-swipe-root` breaks out to `100vw`; a JS shim zeroes ancestor
  padding so the funnel fills the GHL page.

## Steps

**Working directory:** every step runs with cwd = the brand dir (e.g. `acme/`). At the
start, resolve **ROOT** = the nearest ancestor that contains `_system/` (walk up from
cwd), and refer to helpers as `$ROOT/_system/...`. Deliverables live in the target
`swipes/<name>/` folder — which the operator may have pre-created and named.

**STATUS:** keep `SWIPE.md` `STATUS:` naming the phase **currently in progress** —
`PENDING` (scaffolded) → `IMAGES` (images step) → `CLEAN` (cleaning + auditing) →
`DONE` (delivered).

### 0. Locate the swipe folder + scaffold
A **swipe** is a folder under `swipes/` that holds one or more reference `.html` captures
and no finished deliverable yet. It arrives one of two ways:

- **Pre-staged (most common):** the operator already made `swipes/<name>/` and dropped the
  reference(s) inside — e.g. `swipes/zen/…html`, or a multi-page funnel
  `swipes/zen/(adv)…html` + `(pdp)…html`. **Use that folder as-is and keep its name.**
  Do NOT create a new one.
- **Loose capture:** a reference `*.html` sits loose at the brand root (not under
  `brand_info/` / `swipes/` / `docs/`). Capture `DATE=$(date +%F)` once; derive a slug
  (filename → lowercased, non-alphanumerics → `-`, trimmed; fall back to the page
  `<title>` if the filename is generic like `index`/`capture`/a hash); create
  `swipes/<slug>-<brand>-<DATE>/` (append `-2`, `-3`… if it already exists) and move the
  capture inside.

If several swipe folders are pending and the operator didn't name one, ask which (in a
parallel run you'll be told your exact folder). If the chosen folder has no `.html` or is
already built, stop and ask.

Then, for the target folder `swipes/<name>/`:
- Read `brand_info/brand.md` fully + `brand_info/assets/`.
- Ensure the per-swipe scaffold exists: if `SWIPE.md`, `image-manifest.json`,
  `DELIVERY.md`, or `images/` are missing from `swipes/<name>/`, copy them from
  `$ROOT/_system/templates/swipe-folder/`.
- Identify the reference page(s) in the folder. **Multiple `.html` = a multi-page funnel**;
  the filename prefixes are role hints — `(adv)`→advertorial, `(pdp)`→product page,
  `(vsl)`→VSL, etc.
- **Capture-quality gate — do this BEFORE you `cp`.** The base must be a *fully
  self-contained* single-file capture: all JS/CSS/images inlined, **zero external
  `<script src>` / `<link rel=stylesheet>`** (`grep -c '<script[^>]*src=' ref.html` → 0).
  A capture that still points at external scripts won't hydrate when opened as a static
  file — it renders glitchy (stuck carousels, dead tabs, broken buy boxes), which is what
  tempts a forbidden rebuild. If the capture has external deps or looks broken, **re-capture
  the live page with a full-inline tool (e.g. the SingleFile browser extension) and use that
  instead** — a fresh, fully-inlined capture of the same page is a drop-in better base.
  Then **open the capture and eyeball it against the live page before swapping a byte**: a
  clean capture means the whole swipe is just copy/brand/image/link edits on top.
- **Delete SingleFile's CSP meta before anything else.** A SingleFile capture carries
  `<meta http-equiv="content-security-policy" content="default-src 'none'; ...">` so the
  archive cannot phone home. On a deliverable it blocks every image you repoint at the
  brand's own CDN, and it fails **silently**: the markup is right, the URL 200s, the image
  never paints and you go hunting the wrong thing. Strip the meta, then verify one remote
  image renders before doing the image pass.
- **The capture freezes visual state as INLINE styles.** Anything collapsed or
  hidden when the snapshot was taken comes back carrying `style="display:none"`,
  and inline beats every stylesheet rule, so no amount of CSS will reopen it. On
  the pillow swipe six accordion panels were frozen shut this way; the markup was
  right, the new rules were right, and the panels still measured 0px. Strip the
  frozen `display:none` from the panels before styling them. The same applies to
  anything the reference showed conditionally: a drawer, a tooltip, a second tab.
- For each reference page, copy it to a clean deliverable in the same folder named by role
  (`advertorial.html`, `index.html` for the main/PDP page, `vsl.html`, …) and keep the
  original capture as the reference of record. **Edit the deliverable in place — never
  recreate.**
- Set `swipes/<name>/SWIPE.md` `STATUS: PENDING`.

### 0b. Enumerate the mechanics → `MECHANICS.md`
Before estimating anything, find out which of the reference's working parts are
rented apps. What looks like markup is a subscription, and a swipe has parity only
when each one is rebuilt natively, replaced with ours, or explicitly dropped with
the operator's agreement. None of them get silently skipped.

```
python3 $ROOT/_system/scripts/mechanics.py reference.html [.swipe-goat/rendered.html]
```

**Feed it both captures.** A single-file capture has the scripts stripped, so the
`<script src>` naming the vendor is gone. Measured on the pillow swipe: the
single-file reference alone surfaced 8 mechanics; the same file plus the reader's
`rendered.html` surfaced 12, and the three it added (the ESP, the product
personalizer, back-in-stock) were invisible in the capture we were building on.

**Then watch the live page for motion and popups (hard rule 7):**

```
python3 $ROOT/_system/scripts/motion.py <live-url> --out .swipe-goat/motion
```

It loads the page at phone and desktop size, waits for timed popups, scrolls down and
back for scroll triggers, fires exit intent on desktop, and records a video. `MOTION.md`
lists every popup, bar and toast with its trigger and a screenshot, every CSS/JS
animation, everything a script keeps moving, and every number that ticks. Each row goes
into `CONTROLS.md` with how it is rebuilt. Raise `--dwell` (default 25s) if the brand is
known for late popups. Run it on the LIVE URL: the capture has already lost the popups.

The one that usually matters most is the personalisation/preview widget: on a
personalised PDP the preview generated **before** add-to-cart is the conversion
mechanic, not decoration. Budget it as a real build.

### 0c. Inventory every control → `CONTROLS.md`, and start `CROSSREF.md`
Step 0b finds the rented apps. This finds everything else that is supposed to
DO something, because a single-file capture strips every script and each
control whose behaviour lived in JS ships dead while looking finished.

**`CONTROLS.md`: one row per interactive control** (button, link, stepper,
toggle, accordion, tab, slider, dropdown, form, sticky bar, back-to-top, cart
icon): what it must do, how it is rebuilt (native HTML first: `<details>`,
`:checked`, `stepUp()`, a form; a few lines of JS only when native cannot),
and its click-test result on the deliverable AND on the target platform.
Measured on the pillow swipe: the quantity stepper, back-to-top, currency
picker, accordions and Add to cart all rendered perfectly and did nothing.

**`CROSSREF.md`: the swipe is one step of a funnel, so every fact it states
and every handoff it makes gets a source.** Start it now, and update it at
every step that changes copy or wiring, not once at the end:

- **Claims:** price, compare-at, shipping threshold, guarantees and refunds,
  materials and care, specs, origin and address, review counts and ratings,
  vendor and warehouse, any number. Each row: claim | where on the page |
  source of truth (a system, a file, or the operator by name) | date checked.
  A claim with no source is marked `[NEEDS SOURCE]` and fixed before it ships
  as fact. A claim borrowed from a DIFFERENT product is not a source. Offer
  mechanics are the exception to cutting anything: they stay 1:1 and are
  marked `[ADJUST AFTER SWIPE]` (see the prime directive).
- **Handoffs:** every value passed to or from the rest of the funnel: ad and
  SMS link params, product and variant ids, line-item properties, the
  endpoints the page calls, what the order webhook reads. Each row names the
  producer, the consumer, and how the two were checked against each other.

Real misses this catches, all from the pillow swipe: a Dallas warehouse that
contradicted the real Las Vegas printer; a refund promise with no policy
behind it; "machine washable" sourced only from a different pillow; the
widget calling `/api/pillow/...` while the server mounted `/api/scene-preview`;
and the add-on cart post dropping the pet's name, so the shoppers who paid
extra sent orders that could not be made.

### 1. Enumerate images → `image-manifest.json`
- Scan every page for `<img>`, CSS `background-image`, `<source>`, `og:image`, favicon.
- **Classify each image's role accurately** (hero / content / ingredient / review / cta /
  **logo-or-wordmark** / favicon). Don't mistake a small header/footer logo for a hero just
  because its source file's intrinsic dimensions are large — check where/how big it renders.
- For each, record `{ id, slot, role, alt, width, height, aspect, src_original,
  brand_prompt, target_filename, status:"pending" }`. Slot/role names follow this
  convention: `pdp-*`, `adv-*`, `hero-*`, `ingredient-*`, `review-*`, `cta-*`,
  `section-N-*`, `vet-headshot`, etc.
- `brand_prompt` = the **image lock-in prompt** from `brand.md` + the original scene
  reframed for our brand (same composition/role, our product).

### 2. Rewrite copy + reskin brand
- Drive every headline/subhead/body/CTA from `brand.md` voice + offer.
- **Match the reference's copy length/shape per slot.** The layout is tuned to the
  original's character counts — a one-line eyebrow stays one line; a ~3-word ticker bullet
  stays ~3 words; a 2-line subhead stays ~2 lines. Overlong copy wraps, overflows, or gets
  clipped (it stops looking intentional). Fit the slot, then make the words land.
  **Measure it, don't eyeball it:** render at 390px and compare against the reference,
  slot by slot: same line count, no one-word last line, and the highlight span and any
  `<br>` on the same line as before. A 3-line hero headline that became 2 lifted the whole
  first screen 40px; a red second line became one orphan red word.
- Preserve emphasis markup (e.g. accent/teal spans): swap the contents, keep the span.
  Same for inline links and `<br>`: a proof line that ended in "Learn more" keeps a link.
- **Keep each slot's job, not just its length.** A certification checklist stays
  certifications, a citation line stays a citation, a "clinicians' choice" badge keeps its
  avatars only if the new claim is still about people. When the claim changes kind, change
  the icon and decoration with it, or it reads as leftover.
- **Proof slots are filled with the brand's real proof, never bracketed, never deleted.**
  Review counts, star lines, press quotes, press and retailer logo rows, review carousels,
  clinician badges: fill each from `brand.md`. Where the brand has none, keep the section
  as designed (hard rule 5) and get the real proof from the operator before handoff, listed
  in `CROSSREF.md` as `[NEEDS SOURCE]`. Real failure: one swipe shipped
  `[X,XXX]+ VERIFIED REVIEWS`, `"[Press quote goes here.]"`, logo rows of empty outline
  boxes and broken avatar images, and silently deleted the reviews carousel. Every one
  was visible on the first scroll; the audit now fails all four.
- Apply compliance: insert required disclaimers, strip banned words, title-case
  headlines if `brand.md` says so. Never bake copy into images.
- **Swap the brand name/wordmark** everywhere (the reference's brand → ours). Don't leave
  the reference brand's name in headlines, copy, or `<title>`/meta.
- **Trademark glyphs are facts, not styling.** Wherever the brand name appears in running
  copy/meta, use the exact mark the brand really uses (™ vs ®, superscripts, casing),
  verified against the CURRENT product packaging or an operator-confirmed source — never
  guessed, never carried over from the reference. If sources conflict (e.g. the brand's
  own old web assets say ® but current packaging says ™), current packaging + operator
  correction win.
- **Swap the palette → our `brand.md` palette.** List the reference's dominant brand
  colors (`grep -oiE '#[0-9a-f]{3,6}|rgba?\([0-9, .]+\)'` → sort by frequency), map each by
  role to our brand color (accent→accent, CTA→CTA, bg→bg, etc.), and find/replace the hex
  values across the CSS. Only color *values* change; layout/structure stays 1:1. (The logo
  image itself is swapped in Step 3 like any other image.)
  **Map the contrast, not just the hue.** A saturated panel stays saturated, and text on a
  recoloured panel must read at least as well as it did: swapping an orchid and a cyan card
  for lavender and baby pink left their white headline words at ~1.4:1, nearly invisible,
  and the three cards stopped stepping in value. Check each text/background pair you touched.

### 3. Brand images
- Set `SWIPE.md` `STATUS: IMAGES`.
- **Logos & brand marks → the REAL logo file, nothing else.** Every logo/wordmark/favicon
  slot must be filled with the brand's actual logo asset — never generated, never
  re-typeset as HTML/CSS text styled to look like the logo, never a font-approximation,
  never "close enough." Copy the real logo from `brand_info/assets/` into `images/` and
  mark its manifest entry `status:"done"` (no prompt needed). Generate only content/photo
  images.
  - **Verify the asset before trusting it.** `brand_info/assets/` can be stale: open the
    logo and check it glyph-for-glyph against the brand's CURRENT packaging/live site
    (™ vs ®, superscripts, letterforms). Real failure: a stored brand logo (and the
    brand's own funnel) carried an outdated ® while the current carton printed ™. Operator correction always wins over any stored asset.
  - **If no clean, current logo file exists, GET one:** pull it from the brand's live
    site/press kit, ask the operator/brand for the official file, or extract the mark from
    official packaging art (background-knockout of the brand's own carton render is
    acceptable — it is the genuine printed mark). Save the corrected asset back into
    `brand_info/assets/` and quarantine the stale one (rename with `OUTDATED` in the name)
    so no future swipe picks it up.
- **Canonical product lock → no package drift.** Before generating any product-containing
  image, identify the exact product form factor from `brand.md`, the real assets, and any
  operator correction. The operator correction wins if there is ambiguity. Write that lock
  into `image-manifest.json`/`IMAGE-PROMPTS.md`, attach the original reference image and the
  canonical product asset(s) to the same image-model request, and preserve the reference
  composition while changing only the brand/product. Reject and regenerate any output that
  changes the package type, shape, scale, or material (for example box→bag, box→bottle,
  packet→jar, pouch→tub). Do not mark the entry `done` until a side-by-side review against
  both the reference image and canonical product asset passes.
- For each remaining (content/photo) manifest entry, produce the brand image from `brand_prompt` at the entry's
  aspect, **using the path that matches your capabilities:**
  - **You have an image tool** (Codex/ChatGPT image generation): generate it directly,
    write `images/<target_filename>`, optimize (≤1200px longest edge, ~q82, strip
    metadata), then mark `status:"done"` only after the text/no-logo and canonical-product
    QA checks pass.
  - **You have no image tool** (Claude Code builder): run
    `python3 $ROOT/_system/scripts/generate_images.py <swipe-dir>`. When the `codex` CLI is
    installed and logged in, it generates every pending slot through Codex headless (the
    brand lock-in prompt, the reference slot art and `brand_info/assets/` attached, two at
    a time), re-encodes to the slot's format and marks them `generated`. Review each
    against the reference and the canonical product before marking it `done`. Without
    Codex it does **not** block: it writes a placeholder at the right aspect and marks the
    entry `pending`; append those prompts to `IMAGE-PROMPTS.md` (format below).
- Rewrite each HTML image ref (`src`/`srcset`, CSS `url()`) to the relative
  `images/<file>` path. Swapping each image's base64 data-URI for its external brand-image
  path is *how* base64 leaves the file — it's part of the image swap, not a separate
  de-bloat pass. The file otherwise stays a byte-for-byte clone.
- Then `$ROOT/_system/scripts/optimize.py` on `images/`.

**`IMAGE-PROMPTS.md` format** (the Codex-ready handoff the builder emits):
- Top: a one-time **lock-in prefix** = the brand's "Image lock-in prompt" from `brand.md`,
  under a heading that says "paste once, then send each prompt below."
- Then one block per pending image:
  `## <n>. <target_filename> — <aspect>` followed by the full per-image prompt.
- Codex generates each and saves it to `images/<target_filename>` (see
  `$ROOT/_system/CODEX-IMAGES.md`).

### 4. Conservative clean (preserve 1:1)
- Set `SWIPE.md` `STATUS: CLEAN`.
- Make ONLY the minimal edits COC/GHL needs. Do **not** restructure, re-layout, or
  tree-shake CSS. Keep the reference's structure, styles, and classes intact — when unsure,
  keep it.
- Convert `<button>` → `<a>`/styled `<div>` (COC routing). **Preserve the button's display:**
  a bare `<a>` is `display:inline`, so a `width:100%`/centered submit button collapses to
  content width and left-aligns (breaks on mobile). Keep `display:inline-block`/`block` +
  `text-align:center` so the converted control renders exactly like the original button.
- Remove the reference brand's tracking/analytics/pixel scripts (they'd phone home to the
  competitor) and the capture tool's injected junk. Leave functional/layout CSS & JS as-is.
- Mobile: just ensure a `<meta name="viewport">` exists; don't otherwise alter layout.
- **Restore frozen behavior (be 1:1 with the *live* reference, not the static capture).**
  Single-file captures usually strip the JS, freezing dynamic UI — auto-scrolling
  tickers/carousels (often a flex track with `will-change:transform` stuck at a fixed
  `translateX`), countdowns, accordions, tabs. Re-add the intended motion (e.g. a CSS
  marquee: duplicate the track items, `width:max-content`, `@keyframes` translateX `0 →
  -50%` infinite; do NOT use `transform:none!important`, which the cascade lets beat the
  animation). Anything that looks like it should move, make move.
- Optional accelerator (if present): `$ROOT/_system/scripts/clean.py`.

### 5. Stub links
- Every checkout/legal/nav `href` → placeholder. Scrub all live reference-brand URLs
  from `<a href>`, `<form action>`, `<link>` (canonical + favicon), OG/Twitter `url` and
  `image` meta, `srcset`, and JSON-LD bodies — anywhere a competitor URL can hide.

### 6. Audit gate (must pass)
Verify the deliverable passes **every** check below. `$ROOT/_system/scripts/audit.py
<page.html>` automates most of them if present, but the checks themselves are the gate —
run them directly (e.g. with grep) whether or not the script exists:
- no `data:` / base64 URIs anywhere;
- no `<button>` tags;
- every referenced `images/...` file exists on disk (or its manifest entry is `pending`);
- no live non-placeholder URLs anywhere they hide — `<a href>`, `<form action>`,
  `<link>` canonical/favicon, OG/Twitter url+image meta, `srcset`, and JSON-LD — only
  `#` or an `example.com` placeholder;
- **disclaimers:** if `brand.md` lists required disclaimers, each must appear verbatim;
  if it says none are mandated, note that in `DELIVERY.md` and this check passes;
- **no invented/garbled text or reference-brand marks in images:** spot-check the generated
  images for made-up headlines, captions, watermarks, fake logos, or any reference-brand
  trace (placeholders exempt). This does NOT bar the product's own real packaging text and
  wordmark, which are required: get product shots by compositing the canonical asset, never
  by generating (and garbling) the label or stripping its branding;
- **mobile-first visual QA:** for traffic-heavy mobile funnels, review the mobile viewport
  first and compare against the reference funnel side by side before considering desktop.
  For product images, include the canonical product asset in that side-by-side check.
- **QC in Safari, not just Chromium.** Most buyer traffic is iPhone Safari, so the visual
  pass runs on Safari (iOS Safari first, then desktop Safari) before any Chromium browser.
  Chromium (Brave/Chrome) can silently paper over rendering defects that Safari shows every
  real visitor — real failure: Brave filled in a sticky-header gap, so it QC'd clean while
  Safari shipped the gap to production.
- **Sticky/pinned elements must be flush — no island header gap.** Any sticky/fixed header
  (and sticky ATC/footer bar) must pin dead against the viewport edge: `top: 0` (or
  `bottom: 0`), zero margin/offset above it, and an opaque background that spans the full
  width **including the iOS safe-area inset** (pad with `env(safe-area-inset-top)` rather
  than offsetting the element). Page content must never be visible scrolling through a gap
  between the header and the viewport edge. If the design uses an "island"/pill header, the
  strip around it must be opaque page background — never see-through. Scroll-test this in
  Safari specifically (see previous check).
- **structure 1:1:** the deliverable's count of structural landmarks (`<section>`,
  `<header>`, `<footer>`, top-level layout blocks) matches `reference.html`.
  `audit.py index.html --reference reference.html` fails on fewer sections or `<video>`s
  than the capture, on any visible `[...]` placeholder text, and on `<img>` with an empty,
  `#` or `example.com` source.
- **zero reference-brand trace (Hard rule 6):** grep every deliverable file (`index.html`
  **and** all of `ghl/*`) for the reference brand's name + domain — must be 0 hits,
  including slugs/ids/comments. Run:
  `audit.py index.html --forbid <ref-brand> --forbid <ref-domain>` (e.g. `--forbid zen
  --forbid zenblueprint`), and the same on `ghl/page-html-all-in-one.html`.

- **click test (`CONTROLS.md`):** every control exercised in a real browser
  on the deliverable, and again on the target platform after the port. A row
  that has not been clicked is a fail, however finished it looks.
- **layout (pixels, not code):** `python3 $ROOT/_system/scripts/layout.py index.html`
  exits 0. It renders phone and desktop sizes, lets timed popups open, scrolls the
  page through, and fails on sideways scroll, any field or button hanging off its
  card, and any wide field or button off-centre in its card. Every other gate reads
  the code, so a popup whose Sign Up button hung 6px off the card passed them all on
  a pet-portrait swipe; this is the gate that sees it. Run it on the ported page too.
- **motion parity (hard rule 7):** `motion.py index.html --compare
  .swipe-goat/motion/motion.json` exits 0, or every gap it prints is a row in
  `CONTROLS.md` the operator agreed to drop.
- **cross-reference (`CROSSREF.md`):** no `[NEEDS SOURCE]` row, no claim
  without a source, and every handoff checked from both ends. `[ADJUST AFTER
  SWIPE]` offer rows pass: they are listed in `DELIVERY.md` for the operator.

Do not finish until every check is satisfied.

### 7. Port to the target platform
**Ask the operator which platform this swipe is for before packaging: `ghl`,
`shopify`, `checkoutchamps`, or all three.** The swipe itself is platform-neutral,
one self-contained `index.html`; where it goes is the last fork and each platform
wants a different shape. `port.py <page.html> --target <t>` emits it:

| target | shape | the constraint that forces it |
|---|---|---|
| `ghl` | `ghl/` package, 4 files | a Custom HTML element keeps `<style>` but strips `<script>`, and the tracking footer strips `<link rel=stylesheet>`. ~85-100 KB element budget. |
| `shopify` | `shopify/sections/<slug>.liquid` + `assets/` | a section is parsed as **Liquid before it is HTML**, so any literal `{{` or `{%` in the swiped markup fails the theme push. The porter wraps the swiped body in `{% raw %}` and **steps around the Liquid it injects**. It also rewires the buybox (below). |
| `checkoutchamps` | standalone `index.html` + `assets/` | it serves whole pages. Its one documented limit: you may add your own JS but cannot edit the core `index.js`. **The rest of this porter's assumptions are unconfirmed — verify on the first real port and correct them here.** |
| `all` | all three, side by side | when the same offer runs on more than one platform. |

`ghl_export.py` remains the GHL-only entry point and produces byte-identical
output; a test pins the two together.

#### Shopify: the buybox is decoration until it is wired
A swiped PDP's buybox does not sell. The price is literal text, `Add to cart` is a
`type=button` with no form around it, the quantity input has no `name`, and the
upsell checkboxes post nothing. It looks finished and takes no orders, which is the
worst failure mode on the list because nothing about it looks wrong.

`port.py --target shopify` rewires it: wraps the smallest ancestor holding the
control, price and quantity in `{% form 'product', product %}`, adds the hidden
variant id, renames the quantity input, makes the control `type=submit name=add`,
and swaps the hard-coded price for `{{ product.price | money }}`.

- It finds the parts by class heuristics and **prints what each one matched**. Read
  those lines. Override any of them with `--atc` / `--price` / `--compare` / `--qty`
  as CSS selectors, or skip the whole thing with `--no-buybox`.
- If no add-to-cart control is found it says `NOT wired` and changes nothing. It
  never emits a quietly dead buybox.
#### Rebuilding the app mechanics natively
A reference PDP's working parts are usually rented apps, and the swipe only has
parity when they are rebuilt. The pillow reference ran **Candy Rack** (buybox
upsells), **Uploadly** (`data-uploadly-embed`, the photo/preview widget) and
**Judge.me** (reviews). Grep the capture for vendor attributes and CDN hosts
before estimating: what looks like markup is usually a subscription.

**Paid add-ons (the Candy Rack job) are native on Shopify and the porter builds
them.** Each add-on gets its own product/variant; the form posts the main item
plus every checked add-on as line items in one `/cart/add.js` call:

1. Create a product/variant per add-on at its real price.
2. Re-run with `--addon-variant <id>` once per toggle, **in page order**.
3. Verify with a test order. The porter prints what it matched; it cannot prove
   the cart took it.

Behaviour worth knowing before you promise anything:
- **Add-ons post at quantity 1, not the main quantity.** "Rush my order" is
  per-order, and billing it twice on a two-item order is a chargeback waiting to
  happen. For a genuinely per-item add-on set `data-addon-qty="match"` on the toggle.
- **Any failure falls back to the plain form post.** A cart that silently drops
  the main product is worse than one that skips an add-on.
- **Without variant ids the toggles are inert and the porter says `ADD-ONS NOT
  BILLABLE YET`.** It takes the order without the add-on rather than charging
  nothing for it. Do not hand over a swipe showing that line.
- Line-item properties are kept alongside, so the choice still prints on the order.
- Whatever the heuristics matched, **place a test order on the preview theme
  before handing it over.** The form posting is the one thing the audit cannot check.

**Shopify checks the porter cannot make for you** (each one shipped broken on
the pillow swipe before it was caught):
- **The JS asset must parse.** `node --check assets/<slug>.js`. One bad block
  kills every script in the file, so the widget, sticky bar and add-ons all
  die together and nothing on screen says why. (The porter now keeps JSON-LD
  in the markup; it was being glued onto the front of the JS.)
- **Read the cart, not the button.** After a test add, `GET /cart.js` and
  check the line items AND their properties (the pet's name, the preview id,
  add-on flags). Do it once with every add-on ticked.
- **The theme still renders its own chrome.** `theme.liquid` draws its
  header-group and footer-group around every template, so a swipe that
  carries its own header and footer shows two of each. Hide the theme's copies
  scoped to the swipe, and check the theme for a page preloader too.
- **Partners need a share link, not a `preview_theme_id` URL.** That parameter
  is stripped for anyone logged out. Use the preview bar's share link (it
  expires in 2 days) plus the product path, and open it logged out to confirm.


#### GHL specifics
Turn the finished `index.html` into the GHL package in `swipes/<name>/ghl/`:
- **Split:** keep every `<style>` block (goes in the all-in-one); pull every `<script>`
  block out (moves to the tracking footer). The all-in-one must contain **no `<script>`**.
- **Wrap:** put the `<body>` inner HTML inside `<div class="ghl-swipe-root">…</div>`; prepend
  the full-bleed rule (`.ghl-swipe-root{position:relative;left:50%;margin-left:-50vw;
  width:100vw;max-width:100vw;isolation:isolate}`); append the kill-ancestor-padding JS shim
  to the footer file.
- **CDN-ify:** rewrite image `src`/`srcset` from local paths to **absolute CDN URLs** (the
  brand's asset host — set in `brand.md` Link map). Mirror the production CDN path locally
  (`images/brand/foo.png`) so the same path resolves the local file in the standalone and the
  live URL in the package. This is what keeps the all-in-one under GHL's size budget.
- **Fonts:** the capture's base64 `@font-face` are great for the standalone but blow GHL's
  ~85–100 KB budget. `ghl_export.py` strips them and prepends `swipes/<name>/ghl-fonts.css`
  — create that file with the page's real web fonts as a Google Fonts `@import` (keep the
  tiny `local()` "…Placeholder" metric-matchers). The `@import` hoist is semicolon-safe;
  don't hand-edit the URL (Google `css2?family=…wght@400;700` URLs are full of `;`, and a
  split URL parses the whole `<style>` to 0 rules → Framer images balloon to the viewport).
- **Emit:** `page-html-all-in-one.html` (`<style id="ats-<slug>-css">…</style>` + the
  `.ghl-swipe-root` div), `page-tracking.html` (the JS shim + the page's JS), and keep the
  standalone `index.html`.
- Helper: `python3 $ROOT/_system/scripts/ghl_export.py swipes/<name>/index.html --cdn <base-url>
  --slug <our-offer-code>` does the mechanical split/wrap/assemble. **Always pass `--slug`**
  (Hard rule 6 — never let the reference folder name become the element id). Author the
  funnel-specific JS (countdown target, form handler) into the page first so it lands in the
  footer.
- **Lead form wiring is brand-specific.** POST the form to the brand's own lead intake
  (endpoint, payload, consent fields and redirect come from `brand_info/brand.md`), with a
  reference-brand-free `funnel_variant`.

### 8. Write `DELIVERY.md` + finish
- Write `DELIVERY.md` **and** `SWIPE.md` LAST, describing the **final** state of the
  deliverable — not an earlier pass. If you iterate after writing them, update them. A stale
  handoff doc (wrong colors/copy/"pending images"/old offer) misleads whoever deploys it.
- `DELIVERY.md` is the GHL paste SOP for this swipe: which file goes in the Custom HTML
  element, which in the Tracking Footer, the CDN/asset host, the form endpoint, and any
  `pending` images to generate (run Codex on `IMAGE-PROMPTS.md` — see `$ROOT/_system/CODEX-IMAGES.md`).
- Set `SWIPE.md` `STATUS: DONE`.

## Done
Audit passes · every image present (`done`) or flagged `pending` · the **GHL package**
(`ghl/page-html-all-in-one.html` + `ghl/page-tracking.html`) + standalone `index.html`
built · `DELIVERY.md` written · `STATUS: DONE`. Paste-ready into a GHL Custom-HTML element
in one paste.
