# Delivery — <REFERENCE> → <BRAND>

Self-contained funnel folder. **No real URLs are wired** — every link/checkout is a
placeholder. Replace before launch.

## Before going live
1. **Checkout URLs** — replace each placeholder with the real endpoint per purchase
   option / tier / variant.
2. **Legal links** — Terms / Privacy `href="#"` → real URLs.
3. **Canonical / OG / Twitter / JSON-LD** — find-replace `example.com` with the
   production domain across every page file.
4. **Images** — any image marked `PENDING` in `image-manifest.json` must be generated
   and dropped into `images/` before launch.

## Pages
- <index.html — what it is>
- <advertorial.html — what it is>

## Image library
See `image-manifest.json` for slot → filename → role.
