# COC / GHL Handoff Rules — Hard Invariants

Every swipe deliverable MUST satisfy all of these. The `audit` step enforces them.

1. **No `<button>` tags.** They break Checkout Champs routing. Use `<a>` or styled
   `<div>` / `<span>` for any clickable action.
2. **No base64 / encoded images.** No `data:image/…;base64` URIs anywhere. Images are
   external files in the swipe's `images/` folder, referenced by relative path. **Fonts are
   exempt** — base64 fonts inlined by the capture stay as-is (preserves typography 1:1);
   never stub a font URL to a dead placeholder.
3. **No baked copy in images.** All text stays as live HTML text.
4. **No live reference-brand URLs.** Every checkout / legal / nav `href`, plus
   `canonical`, Open Graph, Twitter, and JSON-LD URLs, is stubbed to a placeholder
   (`#` or `https://example.com/...`). Never ship the original brand's links.
5. **Structure stays 1:1.** Replace text nodes and image refs in place. Do not move,
   add, or remove sections versus the reference.

> Source: field-tested swipe SOP + dev-handoff rules (live text, no baked copy,
> compliance disclaimers).
