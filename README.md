# swipe-goat

Claude Code plugin. Send a funnel link and say **"swipe this for `<brand>`"**. It
captures the page as one fully self-contained file, gates the capture, watches the
live page for every animation and popup, then runs the whole swipe runbook: copy,
palette, logo and links into the brand, real images through Codex, the audit, and
the port to Shopify, GHL or Checkout Champ.

```
/plugin marketplace add abovetopsecret/swipe-goat
/plugin install swipe-goat@swipe-goat
```

Delivery page: https://sg.abovetopsecret.ai

## The engine ships inside

`_system/` is the swipe engine: `RUNBOOK.md` (the doctrine), the audit, the porter,
`motion.py`, the image driver and the templates. The engine repo is still the source
of truth. A workspace that has its own `_system/` uses it, so an operator's machine
never runs a stale copy. This bundled copy exists so a fresh install, with nothing
but a `<brand>/brand_info/brand.md`, can run a whole swipe.

`scripts/release.sh` refreshes it from the engine repo and runs every test before a
release. Nothing else writes to `_system/` here: change the engine, then release.

## The two scripts

| script | job |
|---|---|
| `swipe-capture.mjs` | the swipe base. SingleFile, scripts blocked, gated. |
| `capture.mjs` | the reader. Section order, type ramp, palette, copy, screenshots. Research only, and its output would fail the gate. |
| `release.sh` | sync the engine from its repo, check versions match, run every test. |

The second one exists because the two jobs are different. Cloning a reference
funnel into a client's brand is the swipe pipeline. Studying a competitor in our
own market on our own product is a rebuild, and the reader is what you build from.

## The gate

A capture that still points at external scripts does not hydrate when opened as a
static file. It renders glitchy, and a glitchy base is what tempts the rebuild the
prime directive exists to prevent. So the gate runs automatically, not as a grep
in a checklist:

- zero external `<script src>`
- zero external stylesheet links
- enough visible text that the capture is a page and not a bot-block shell

A failed gate is never a licence to rebuild. Re-capture with the SingleFile
browser extension in your own signed-in Chrome and drop the file in the folder.
