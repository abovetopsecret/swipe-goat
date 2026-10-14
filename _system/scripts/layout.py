#!/usr/bin/env python3
"""Does everything physically fit? The audit reads code; this measures pixels.

  python3 layout.py <page.html|url> [--viewports mobile,desktop] [--dwell 6]

Per viewport it loads the page, waits for popups to open, checks, then scrolls
the page through and checks again. It flags:

  - sideways scroll: anything wider than the screen;
  - a field or button hanging off the card it sits in (popup, panel, product
    card), the way a pet-portrait swipe's Sign Up button did;
  - a wide field or button visibly off-centre in its card.

Only what is actually on screen is checked: a control counts when it is what
a tap at its centre would hit, so hidden drawers and closed popups are skipped
until they open. Exits 1 when anything is flagged.
"""
import argparse, json, pathlib, re, sys

CHECK_JS = r"""
() => {
  const out = [];
  const W = innerWidth;
  const sel = (el) => {
    const p = [];
    for (let n = el, i = 0; n && n.nodeType === 1 && i < 3; n = n.parentElement, i++) {
      let s = n.tagName.toLowerCase();
      if (n.id) { p.unshift(s + '#' + n.id); break; }
      const c = [...n.classList].slice(0, 2); if (c.length) s += '.' + c.join('.');
      p.unshift(s);
    }
    return p.join(' > ');
  };
  const onScreen = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.bottom <= 0 || r.top >= innerHeight) return null;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || +cs.opacity < 0.1) return null;
    const x = Math.min(W - 1, Math.max(0, r.left + Math.min(r.width, 40) / 2));
    const hit = document.elementFromPoint(x, Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2)));
    return hit && (hit === el || el.contains(hit) || hit.contains(el)) ? r : null;
  };
  // 1. sideways scroll
  if (document.documentElement.scrollWidth > W + 1) {
    const wide = [...document.querySelectorAll('body *')].filter((e) => {
      const r = e.getBoundingClientRect(); return r.width > 0 && r.right > W + 1 && getComputedStyle(e).position !== 'fixed';
    });
    const outer = wide.filter((e) => !wide.some((o) => o !== e && o.contains(e))).slice(0, 5);
    out.push({ kind: 'sideways scroll', detail: `page is ${document.documentElement.scrollWidth}px on a ${W}px screen`,
               where: outer.map(sel) });
  }
  // 2 + 3. controls against their card
  const isCard = (n) => {
    const cs = getComputedStyle(n);
    const bg = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent';
    const edge = parseFloat(cs.borderLeftWidth) > 0 || cs.boxShadow !== 'none' || parseFloat(cs.borderTopLeftRadius) > 4;
    const r = n.getBoundingClientRect();
    return (bg || edge) && r.width < W - 2 && r.width > 120;
  };
  const controls = [...document.querySelectorAll(
    'input:not([type=hidden]):not([type=checkbox]):not([type=radio]), button, select, textarea, a[role=button], a[class*=btn], a[class*=button], [class*=button][onclick]'
  )];
  for (const el of controls) {
    const r = onScreen(el); if (!r) continue;
    let card = el.parentElement;
    while (card && card !== document.body && !isCard(card)) card = card.parentElement;
    if (!card || card === document.body) continue;
    const c = card.getBoundingClientRect();
    const left = r.left - c.left, right = c.right - r.right;
    if (left < -1 || right < -1) {
      out.push({ kind: 'hangs off its card', where: [sel(el)], card: sel(card),
                 detail: `${Math.round(Math.max(-left, -right))}px past the card's ${left < -1 ? 'left' : 'right'} edge` });
    } else if (r.width > 0.5 * c.width && Math.abs(left - right) > 8 && getComputedStyle(card).textAlign !== 'left') {
      out.push({ kind: 'off-centre in its card', where: [sel(el)], card: sel(card),
                 detail: `${Math.round(left)}px from the left edge, ${Math.round(right)}px from the right` });
    }
  }
  return out;
}
"""

VIEWPORTS = {
    "mobile": "iPhone 13",
    "desktop": None,
}


def check(browser, p, url, vp, dwell):
    opts = p.devices[VIEWPORTS[vp]] if VIEWPORTS[vp] else {"viewport": {"width": 1440, "height": 900}}
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(dwell * 1000)
    found = page.evaluate(CHECK_JS)                     # popups that open on a timer are on screen now
    page.keyboard.press("Escape")
    h = page.evaluate("document.documentElement.scrollHeight")
    step = int(page.evaluate("innerHeight") * 0.8)
    for y in range(0, h + step, step):
        page.evaluate(f"scrollTo(0,{y})")
        page.wait_for_timeout(120)
        found += page.evaluate(CHECK_JS)
    ctx.close()
    seen, uniq = set(), []
    for f in found:
        k = (f["kind"], tuple(f["where"]))
        if k not in seen:
            seen.add(k); uniq.append(f)
    return uniq


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--viewports", default="mobile,desktop")
    ap.add_argument("--dwell", type=int, default=6, help="seconds to let timed popups open first")
    ap.add_argument("--json", help="write findings here too")
    a = ap.parse_args()
    url = a.target if re.match(r"https?://", a.target) else pathlib.Path(a.target).resolve().as_uri()
    from playwright.sync_api import sync_playwright
    result = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for vp in a.viewports.split(","):
            result[vp] = check(b, p, url, vp, a.dwell)
        b.close()
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(result, indent=2))
    bad = 0
    for vp, items in result.items():
        print(f"{vp}: {len(items)} layout problem(s)")
        for f in items:
            bad += 1
            card = f" (card {f['card']})" if f.get("card") else ""
            print(f"  {f['kind']}: {', '.join(f['where'])}{card}\n    {f['detail']}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
