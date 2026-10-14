#!/usr/bin/env python3
"""Pre-handoff audit: enforce COC/GHL hard rules on a swipe page.

Usage: python3 audit.py <page.html> [--images DIR] [--require "exact text" ...]
                       [--forbid "zen" ...] [--allow client-domain.com ...]
                       [--reference reference.html]
Exit non-zero (and print the violations) if any rule fails.
"""
import argparse, pathlib, re, sys

PLACEHOLDER_HOSTS = ("example.com",)

def find_violations(html: str, page: pathlib.Path, images_dir: pathlib.Path,
                    required_texts, forbidden_tokens=(), allowed_hosts=(),
                    reference_html=None):
    v = []

    # 0. no reference-brand tokens ANYWHERE — the deliverable must carry zero trace of
    #    the funnel it was swiped from (names, slugs, ids, comments). Pass the reference
    #    brand's name(s) via --forbid.
    #
    #    SUBSTRING, not word-boundary: a word-boundary match PASSED a page full of
    #    "zenblueprint" when told to forbid "zen", and glued into an id, a class, a
    #    slug or a filename is exactly where a brand token survives a clean. The
    #    whole word each hit sits in is reported, so a real false positive
    #    ("zenith" on a zen swipe) is obvious and the token can be narrowed.
    #    Base64 payloads are random bytes, so a short token hits them by chance:
    #    forbidding "zen" matched 37 inlined font blobs on a real deliverable.
    #    Rule 2 below still sees the data: prefix, only the payload is cut.
    unencoded = re.sub(r"(data:[^;,\"')]*;base64,)[A-Za-z0-9+/=\s]+", r"\1", html)
    for tok in forbidden_tokens:
        tok = tok.strip()
        if not tok:
            continue
        hits = {}
        for m in re.findall(r"[\w-]*" + re.escape(tok) + r"[\w-]*", unencoded, re.I):
            hits[m.lower()] = hits.get(m.lower(), 0) + 1
        if hits:
            top = sorted(hits.items(), key=lambda kv: -kv[1])[:8]
            where = ", ".join(f"{w} ({n}x)" for w, n in top)
            v.append(f"reference-brand token leaked {sum(hits.values())}x "
                     f"(must be 0): {tok!r} in {where}")

    # 1. no <button>
    if re.search(r"<button\b", html, re.I):
        v.append("found <button> tag (breaks COC routing)")

    # 2. no base64 IMAGES (fonts inlined by the capture are exempt — keeping them
    #    base64 preserves typography 1:1; the rule targets heavy/COC-breaking images)
    if re.search(r"data:image/[^\"')]*;base64,", html, re.I):
        v.append("found base64 image data: URI (no encoded images allowed)")

    def srcset_urls(attrval):
        # "a.jpg 1x, b.jpg 480w" -> ["a.jpg", "b.jpg"]
        out = []
        for part in attrval.split(","):
            tok = part.strip().split()
            if tok:
                out.append(tok[0])
        return out

    # 3. referenced local images must exist (src/href, css url(), and srcset)
    refs = set(re.findall(r'(?:src|href)\s*=\s*["\'](images/[^"\']+)["\']', html, re.I))
    refs |= set(re.findall(r'url\(\s*["\']?(images/[^)"\']+)', html, re.I))
    for ss in re.findall(r'srcset\s*=\s*["\']([^"\']+)["\']', html, re.I):
        refs |= {u for u in srcset_urls(ss) if u.startswith("images/")}
    for rel in sorted(refs):
        if not (page.parent / rel).exists():
            v.append(f"referenced image missing on disk: {rel}")

    # 4. no live (non-placeholder) URLs anywhere they can hide (hard rule 4):
    #    <a href>, <form action>, <link href> (canonical/favicon), OG/Twitter url+image
    #    meta, srcset, and any URL inside JSON-LD bodies.
    # Hosts whose live URLs belong in the deliverable: the placeholders, plus
    # whatever the operator declared with --allow. Without this the gate failed
    # every finished swipe on the CLIENT'S OWN privacy-policy and terms links, and
    # a gate that cannot pass correct work is a gate that stops being read.
    hosts = PLACEHOLDER_HOSTS + tuple(
        re.sub(r"^\w+://", "", h.strip().lower()).strip("/").split("/")[0]
        for h in allowed_hosts if h.strip())

    def is_live(url):
        u = url.strip()
        if (not u or u[0] in "#?" or u.startswith("/") or u.startswith("images/")
                or u.startswith("data:") or u.startswith("mailto:")
                or u.startswith("tel:")):
            return False
        m = re.match(r"https?://([^/]+)", u, re.I)
        if not m:
            return False
        host = m.group(1).lower()
        return not any(host == h or host.endswith("." + h) for h in hosts)

    def flag(url, label):
        if is_live(url):
            v.append(f"live {label} (stub it): {url}")

    for url in re.findall(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']', html, re.I):
        flag(url, "href")
    for url in re.findall(r'<form\b[^>]*\baction\s*=\s*["\']([^"\']+)["\']', html, re.I):
        flag(url, "form action")
    # <link> with rel canonical/icon — match either attribute order
    for url in re.findall(r'<link\b[^>]*\brel\s*=\s*["\'][^"\']*(?:canonical|icon)[^"\']*'
                          r'["\'][^>]*\bhref\s*=\s*["\']([^"\']+)', html, re.I):
        flag(url, "link href")
    for url in re.findall(r'<link\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*\brel\s*=\s*'
                          r'["\'][^"\']*(?:canonical|icon)[^"\']*["\']', html, re.I):
        flag(url, "link href")
    # OG/Twitter url+image meta — match either attribute order
    og = r'(?:og:url|og:image|twitter:url|twitter:image)'
    for url in re.findall(r'<meta\b[^>]*(?:property|name)\s*=\s*["\']' + og +
                          r'["\'][^>]*content\s*=\s*["\']([^"\']+)', html, re.I):
        flag(url, "OG/Twitter URL")
    for url in re.findall(r'<meta\b[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*'
                          r'(?:property|name)\s*=\s*["\']' + og + r'["\']', html, re.I):
        flag(url, "OG/Twitter URL")
    for ss in re.findall(r'srcset\s*=\s*["\']([^"\']+)["\']', html, re.I):
        for u in srcset_urls(ss):
            flag(u, "srcset URL")
    for body in re.findall(r'<script\b[^>]*type\s*=\s*["\']application/ld\+json["\']'
                           r'[^>]*>(.*?)</script>', html, re.I | re.S):
        for url in re.findall(r'https?://[^\s"\'<>\\]+', body):
            flag(url, "JSON-LD URL")

    # 5. required disclaimers / texts present
    for t in required_texts:
        if t and t not in html:
            v.append(f"required text missing: {t!r}")

    # 6. no unfilled slot a visitor can SEE. A real swipe shipped "[X,XXX]+ VERIFIED
    #    REVIEWS", "[Press quote goes here.]" and logo rows of empty boxes, and every
    #    other check passed it. Footnote refs like [1] are fine.
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"""<(?:[^>"']|"[^"]*"|'[^']*')*>""", " ", text)  # quoted attrs hold ">"
    for tok in sorted(set(re.findall(r"\[(?!\d+\])[^\]\n<]{1,60}\]", text))):
        v.append(f"placeholder text visible on the page: {tok}")
    for src in re.findall(r'<img\b[^>]*\ssrc\s*=\s*["\']([^"\']*)["\']', html, re.I):
        if not src.strip() or src.strip() == "#" or "example.com" in src:
            v.append(f"<img> with no real source renders broken or empty: {src!r}")

    # 7. structure 1:1 against the capture (hard rules 5 and 7). A reviews section
    #    with nothing to fill it got deleted, and two videos became stills.
    if reference_html is not None:
        for what, pat in (("sections", r"<(?:section|header|footer)\b"),
                          ("videos", r"<video\b")):
            ref, ours = (len(re.findall(pat, h, re.I)) for h in (reference_html, html))
            if ours < ref:
                v.append(f"{what}: reference has {ref}, deliverable has {ours} "
                         f"(something was dropped)")

    return v

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--images", default=None)
    ap.add_argument("--require", action="append", default=[])
    ap.add_argument("--forbid", action="append", default=[],
                    help="reference-brand token(s) that must NOT appear anywhere "
                         "in the deliverable (e.g. --forbid zen --forbid zenblueprint)")
    ap.add_argument("--allow", action="append", default=[],
                    help="host(s) whose live URLs are legitimate here — the "
                         "client's own domain (e.g. --allow go.example-client.com)")
    ap.add_argument("--reference", default=None,
                    help="the capture this swipe was copied from; fails if the "
                         "deliverable has fewer sections or videos")
    a = ap.parse_args()

    page = pathlib.Path(a.page)
    if not page.exists():
        print(f"AUDIT ERROR: page not found: {page}", file=sys.stderr)
        return 2
    images_dir = pathlib.Path(a.images) if a.images else page.parent / "images"
    html = page.read_text(encoding="utf-8", errors="replace")
    ref = (pathlib.Path(a.reference).read_text(encoding="utf-8", errors="replace")
           if a.reference else None)
    v = find_violations(html, page, images_dir, a.require, a.forbid, a.allow, ref)

    if v:
        print(f"AUDIT FAILED ({len(v)}) for {page}:")
        for item in v:
            print(f"  - {item}")
        return 1
    print(f"AUDIT PASSED: {page}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
