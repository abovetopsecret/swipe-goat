#!/usr/bin/env python3
"""Find the app-driven mechanics in a captured page and write the build list.

A reference page's working parts are usually rented. What looks like markup is a
subscription: the upsell toggles are Candy Rack, the photo/preview widget is
Uploadly, the stars are Judge.me. A swipe only has parity once each one is
rebuilt, so the first thing to know is which ones are there.

They are easy to miss. A SingleFile capture has the scripts stripped, so the
<script src> that would name the vendor is gone and only class names, data
attributes and leftover CSS remain. Run this on the richest input available:

  python3 mechanics.py <page.html> [more.html ...] [--out MECHANICS.md]

Feed it BOTH the single-file reference and, if you have one, the Playwright
rendered.html from the reader capture. The reader keeps every external script
src and will name vendors the single-file capture cannot.
"""
import argparse, pathlib, re, sys

# signature -> (vendor, what it does for the visitor, what rebuilding it takes)
APPS = [
    (r"uploadly", "Uploadly", "photo upload + live personalised preview before add-to-cart",
     "file input -> your upload endpoint -> render the preview -> attach the asset URL as a "
     "line-item property. This is usually THE conversion mechanic on a personalised PDP: "
     "the micro-commitment before the ask. Budget it as a real build, not a section."),
    (r"candyrack|candy-rack", "Candy Rack", "paid add-on toggles in the buybox",
     "port.py --target shopify rebuilds this natively: a variant per add-on, posted as line "
     "items via /cart/add.js. Supply --addon-variant per toggle."),
    (r"judge\.me|jdgm", "Judge.me", "review stars, review cards, shop medals",
     "a reviews section fed by your own review data. Never carry the reference's reviews, "
     "rating counts or medals across: they are claims about THEIR shop."),
    (r"loox|okendo|stamped\.io|yotpo", "reviews app", "reviews and UGC galleries",
     "same as Judge.me: your own review data or an empty shell."),
    (r"teeinblue|customily|kickflip|zakeke|printify|printful", "product personalizer",
     "live product customisation and print-file generation",
     "your own generator plus a preview endpoint. Check whether the print pipeline you "
     "already run can serve the preview before pricing an app."),
    (r"zipify|reconvert|aftersell", "post-purchase upsell", "the offer shown after checkout",
     "a post-purchase page on your platform. Out of scope for the page swipe itself: "
     "flag it so it is not silently dropped from the funnel."),
    (r"rebuy|wiser", "recommendations", "cross-sell carousels",
     "a hand-picked collection, or your own recommendation query."),
    (r"klaviyo|omnisend|attentive", "ESP / capture", "email + SMS capture popups and flows",
     "your own ESP or drip engine. Capture forms post to YOUR endpoint, never the reference's."),
    (r"gorgias|tidio|intercom|zendesk", "helpdesk chat", "the chat bubble",
     "your own helpdesk, or remove it. Never ship the reference's: it opens THEIR inbox."),
    (r"vidalytics|wistia|vimeo|jwplayer", "video player", "the VSL player",
     "your own player embed. These ship their own <button> and a live 'powered by' link, "
     "which will trip the audit."),
    (r"uppromote|refersion|goaffpro", "affiliate app", "affiliate signup",
     "REMOVE. The reference's link carries THEIR affiliate id and enrols your visitor "
     "under them."),
    (r"sezzle|klarna|afterpay|affirm|shop-pay-installment", "BNPL widget", "pay-in-4 messaging",
     "your own provider's widget, and only if you actually offer it. It is a pricing claim."),
    (r"smile\.io|loyaltylion|yotpo-loyalty", "loyalty", "points and rewards messaging",
     "your own programme, or remove. It is a promise to the customer."),
    (r"back-in-stock|backinstock|notify-?me", "back-in-stock", "restock notifications",
     "your own notify form posting to your endpoint."),
    (r"gempages|pagefly|shogun|zipify-pages", "page builder", "how the reference built the page",
     "not a mechanic: it just means the markup is builder output. Expect verbose wrappers."),
]

# Anything carrying an embed/widget hook is a mechanic even when the vendor is unknown.
GENERIC = re.compile(r'data-([a-z0-9-]{3,24})-(?:embed|widget|app|root)\b', re.I)


def scan(texts):
    blob = "\n".join(texts)
    hits = []
    for pat, vendor, does, rebuild in APPS:
        n = len(re.findall(pat, blob, re.I))
        if n:
            hits.append((n, vendor, does, rebuild))
    known = " ".join(h[1].lower() for h in hits)
    unknown = {}
    for m in GENERIC.finditer(blob):
        name = m.group(1).lower()
        if name not in known:
            unknown[name] = unknown.get(name, 0) + 1
    return sorted(hits, reverse=True), unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--out", default=None, help="write the build list here (default: MECHANICS.md beside the first page)")
    a = ap.parse_args()

    texts, names = [], []
    for name in a.pages:
        p = pathlib.Path(name)
        if not p.exists():
            print(f"skipping missing file: {p}", file=sys.stderr); continue
        texts.append(p.read_text(encoding="utf-8", errors="replace")); names.append(p.name)
    if not texts:
        print("no readable pages", file=sys.stderr); return 2

    hits, unknown = scan(texts)
    out = pathlib.Path(a.out) if a.out else pathlib.Path(a.pages[0]).parent / "MECHANICS.md"

    lines = ["# Mechanics to rebuild", "",
             "Scanned: " + ", ".join(names), "",
             "Every one of these is a rented app on the reference. The swipe has parity "
             "only when each is rebuilt natively, replaced with our own, or explicitly "
             "dropped with the operator's agreement. None of them get silently skipped.", ""]
    if not hits and not unknown:
        lines += ["Nothing matched. If the page clearly does something interactive, scan the "
                  "Playwright `rendered.html` too: a single-file capture has the scripts "
                  "stripped and hides the vendor.", ""]
    for n, vendor, does, rebuild in hits:
        lines += [f"## {vendor}  ({n} references)", "",
                  f"**Does:** {does}", "", f"**Rebuild:** {rebuild}", ""]
    if unknown:
        lines += ["## Unidentified embeds", "",
                  "Carrying an embed/widget hook with no known vendor. Open the capture and "
                  "see what each one does before assuming it is decoration.", ""]
        lines += [f"- `data-{k}-*` ({v} references)" for k, v in sorted(unknown.items(), key=lambda kv: -kv[1])]
        lines += [""]
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"{len(hits)} known mechanic(s), {len(unknown)} unidentified -> {out}")
    for n, vendor, does, _ in hits:
        print(f"   {n:4}  {vendor:22} {does}")
    for k, v in sorted(unknown.items(), key=lambda kv: -kv[1]):
        print(f"   {v:4}  data-{k}-*{' ' * max(0, 13 - len(k))} (unidentified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
