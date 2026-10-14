# CODEX-IMAGES.md — Image Factory (Codex)

You are the **image factory** for a swipe that Claude already built. You **only make
images** — do not touch the HTML, copy, or structure.

Given a swipe folder (`<brand>/swipes/<name>/`):

1. Read `IMAGE-PROMPTS.md`. The top block is the brand **lock-in prefix** — prepend it to
   every image prompt so the whole set stays on-brand and consistent.
   If the file has a **Canonical Product Lock**, treat it as mandatory. The operator's
   latest correction wins over older prompt text or ambiguous brand notes.
2. For each numbered entry `## <n>. <filename> — <aspect>`, generate the image at that
   aspect and save it as `images/<filename>`, **overwriting the placeholder of the same
   name**. Optimize to ≤1200px on the longest edge if you can.
   Send the listed reference image and any canonical product asset(s) in the same model
   request as the prompt so the model can preserve the reference composition without
   drifting the product.
3. Review the result side by side with the reference image and the canonical product asset.
   Set that entry's `status` to `"done"` in `image-manifest.json` only after it passes.

Rules:
- Generated (non-product) images must be free of invented or garbled text, fake logos, and
  any trace of the reference brand; regenerate if such text/marks appear. This does NOT bar
  the product's own real packaging text or wordmark, which are required.
- Prefer a REAL canonical product photo over a generated one: image models garble packaging
  text, so composite the canonical asset rather than generating the pouch/bag/treat/label.
  Generated product is off-model; never strip the product's own branding to satisfy "no text".
- Product-containing images must preserve the canonical product form factor exactly. Reject
  and regenerate if the model turns a box into a bag/pouch/bottle/jar/tub/dropper, changes
  the package material, or makes the product look like an unapproved SKU.
- Keep filenames and aspects exactly as listed — the HTML already points at them.
- Don't add, remove, or rename image slots. If a prompt is unclear, generate the closest
  faithful interpretation; don't invent new images.

When every entry is `done`, the swipe's audit will pass fully and the folder is ready for
handoff.
