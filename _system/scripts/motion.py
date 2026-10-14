#!/usr/bin/env python3
"""Inventory a page's animations and popups by watching it like a shopper.

A single-file capture is a snapshot. It keeps CSS keyframes and loses the rest:
popups that are not in the DOM yet (timed, scroll, exit-intent), and everything
JS moves (carousels, tickers, countdowns, counters, sticky bars that slide in).
Parity includes all of it, so this records what the LIVE page does and writes
the list the swipe has to match.

  python3 motion.py <url-or-file> [--out DIR] [--dwell 25] [--compare ref/motion.json]

Per viewport (mobile first, then desktop): dwell for timed popups, scroll down
and back for scroll triggers, then fire exit intent (desktop). Writes
MOTION.md + motion.json + a video per viewport + a screenshot per popup.
--compare lists what the reference had that this page does not.
"""
import argparse, json, pathlib, re, sys, time

WATCH_JS = r"""
(() => {
  if (window.__motion) return;
  const M = window.__motion = { phase: 'load', t0: performance.now(), events: [], anims: {}, moveMap: new WeakMap(), moveList: [], text: {}, seen: new WeakSet(), base: null };
  const sel = (el) => {
    const out = [];
    for (let n = el, i = 0; n && n.nodeType === 1 && i < 3; n = n.parentElement, i++) {
      let s = n.tagName.toLowerCase();
      if (n.id) { out.unshift(s + '#' + n.id); break; }
      const c = [...n.classList].filter((x) => !/^(is-|js-|active|open|show)/.test(x)).slice(0, 2);
      if (c.length) s += '.' + c.join('.');
      out.unshift(s);
    }
    return out.join(' > ');
  };
  M.sel = sel;
  const now = () => Math.round((performance.now() - M.t0) / 100) / 10;
  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.1) return null;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 24) return null;
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return null;
    // Showing means it is what a tap at its centre would hit. Off-canvas drawers
    // and menus are in the DOM, displayed and sized, but parked off-screen or
    // under something; without this they read as popups that never appear.
    const cx = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2));
    const cy = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || !(el === hit || el.contains(hit))) return null;
    return r;
  };
  // Fixed/sticky/dialog elements that are showing right now.
  const overlays = () => {
    const out = [];
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      const dialog = el.getAttribute('role') === 'dialog' || el.getAttribute('aria-modal') === 'true' || el.tagName === 'DIALOG';
      if (cs.position !== 'fixed' && cs.position !== 'sticky' && !dialog) continue;
      const r = visible(el);
      if (r) out.push([el, r]);
    }
    return out;
  };
  M.poll = () => {
    const vis = overlays();
    if (!M.base) { M.base = new WeakSet(vis.map(([el]) => el)); vis.forEach(([el]) => M.seen.add(el)); return; }
    for (const [el, r] of vis) {
      if (M.seen.has(el) || M.base.has(el)) continue;
      // Report the outermost new overlay, not every child of the same popup.
      let p = el.parentElement, nested = false;
      while (p) { if (M.seen.has(p)) { nested = true; break; } p = p.parentElement; }
      M.seen.add(el);
      if (nested) continue;
      const area = (r.width * r.height) / (innerWidth * innerHeight);
      M.events.push({ t: now(), phase: M.phase, scroll: Math.round(100 * scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight)),
        // Pinned to the top or bottom edge is a bar (sticky header, sticky ATC,
        // announcement) unless it fills most of the screen.
        kind: (r.top < 2 || r.bottom > innerHeight - 2) && area < 0.35 ? 'bar' : (area >= 0.08 ? 'popup' : 'toast'),
        sel: sel(el), text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 90), area: Math.round(area * 100) });
      el.setAttribute('data-motion-shot', String(M.events.length - 1));
    }
    for (const a of document.getAnimations()) {
      const target = a.effect && a.effect.target;
      if (!target) continue;
      const name = a.animationName || a.transitionProperty || 'script (Web Animations)';
      const timing = a.effect.getTiming();
      const key = name + ' @ ' + sel(target);
      if (!M.anims[key]) M.anims[key] = { name, sel: sel(target), type: a.constructor.name,
        duration: timing.duration, infinite: timing.iterations === Infinity, first: now(), phase: M.phase };
    }
  };
  // Timer first: the observer below can only attach once there is a document
  // to watch, and a throw there must not take the polling down with it.
  setInterval(M.poll, 400);
  // JS motion: inline style/class churn and text that keeps changing. Watch
  // `document` itself: init scripts run before <html> exists, and observing a
  // null documentElement throws. Setting textContent swaps the text node, so
  // that arrives as childList, not characterData.
  new MutationObserver((muts) => {
    for (const m of muts) {
      const el = m.type === 'characterData' ? m.target.parentElement : m.target;
      if (!el || el.nodeType !== 1 || el.closest('[data-motion-ignore]')) continue;
      if (m.type === 'attributes') {
        // Per ELEMENT, not per selector: thirty product images share one class,
        // and pooling them made a lazy-load look like a carousel.
        let v = M.moveMap.get(el);
        if (!v) { v = { el, sel: sel(el), attr: m.attributeName, n: 0, cycles: 0, seenCls: new Set(), first: now() }; M.moveMap.set(el, v); M.moveList.push(v); }
        v.n++;
        // A class only counts as motion when an earlier value comes back round
        // (a carousel's "active" returns; a lazy-load never goes back).
        if (m.attributeName === 'class') {
          const c = el.getAttribute('class') || '';
          if (v.seenCls.has(c)) v.cycles++; else v.seenCls.add(c);
        }
      } else if (m.type === 'childList' && [...m.addedNodes].some((n) => n.nodeType === 1)) {
        continue; // structure being built, not a number ticking
      } else if (/\d/.test(el.textContent || '') && (el.textContent || '').length < 60) {
        const k = sel(el), v = M.text[k] || (M.text[k] = { sel: k, n: 0, sample: '', el });
        v.n++; v.sample = (el.textContent || '').trim().slice(0, 40);
      }
    }
  }).observe(document, { subtree: true, attributes: true, attributeFilter: ['style', 'class'], characterData: true, childList: true });
})();
"""

VIEWPORTS = {
    "mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                   user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"),
    "desktop": dict(viewport={"width": 1440, "height": 900}),
}


def close_popup(page):
    page.keyboard.press("Escape")
    for s in ['[aria-label*="close" i]', '[class*="close" i]', 'button:has-text("No thanks")', 'button:has-text("×")']:
        try:
            el = page.locator(s).first
            if el.is_visible(timeout=200):
                el.click(timeout=500)
                return
        except Exception:
            pass


def watch(browser, url, name, out, dwell):
    ctx = browser.new_context(record_video_dir=str(out / "video"), **VIEWPORTS[name])
    ctx.add_init_script(WATCH_JS)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.evaluate("window.__motion.poll()")  # baseline: what is fixed on screen at first paint

    shots = 0

    def tick(ms):
        nonlocal shots
        end = time.time() + ms / 1000
        while time.time() < end:
            page.wait_for_timeout(400)
            n = page.evaluate("window.__motion.events.length")
            while shots < n:
                try:
                    page.screenshot(path=str(out / f"{name}-event-{shots}.png"))
                except Exception:
                    pass
                close_popup(page)
                shots += 1

    page.evaluate("window.__motion.phase = 'dwell'")
    tick(dwell * 1000)
    page.evaluate("window.__motion.phase = 'scroll'")
    height = page.evaluate("document.documentElement.scrollHeight")
    step = int(VIEWPORTS[name]["viewport"]["height"] * 0.6)
    for y in list(range(0, height, step)) + list(range(height, -1, -step * 2)):
        page.evaluate(f"window.scrollTo(0, {y})")
        tick(450)
    if name == "desktop":
        page.evaluate("window.__motion.phase = 'exit-intent'")
        page.mouse.move(700, 300)
        page.mouse.move(700, 1)
        page.evaluate("""() => {
          const e = (t) => new MouseEvent(t, { clientX: 700, clientY: -2, relatedTarget: null, bubbles: true });
          document.dispatchEvent(e('mouseout')); document.documentElement.dispatchEvent(e('mouseleave'));
        }""")
        tick(2500)
    data = page.evaluate("""() => { const M = window.__motion; M.poll();
      return { events: M.events, anims: Object.values(M.anims),
               // A moving REGION: elements a script keeps moving (6+ style changes,
               // or a class that cycles back), grouped by parent so a carousel's
               // slides count once, then nested regions folded into the outer one.
               moves: (() => {
                 const skip = (e) => !e || e === document.body || e === document.documentElement;
                 const moving = M.moveList.filter((v) => v.el.isConnected && !skip(v.el) &&
                   ((v.attr === 'style' && v.n >= 6) || (v.n >= 6 && v.cycles >= 3)));
                 const groups = new Map();
                 for (const v of moving) {
                   const host = skip(v.el.parentElement) ? v.el : v.el.parentElement;
                   const g = groups.get(host) || { host, sel: M.sel(host), n: 0, items: 0, first: v.first };
                   g.n += v.n; g.items++; g.first = Math.min(g.first, v.first); groups.set(host, g);
                 }
                 const all = [...groups.values()];
                 return all.filter((g) => !all.some((o) => o !== g && o.host.contains(g.host)))
                           .map(({ host, ...rest }) => ({ ...rest, attr: rest.items + ' moving child' + (rest.items > 1 ? 'ren' : '') }));
               })(),
               counters: (() => { const c = Object.values(M.text).filter((v) => v.n >= 3);
                 return c.filter((v) => !c.some((o) => o !== v && v.el.contains(o.el)))
                         .map(({ el, ...rest }) => rest); })() }; }""")
    video = page.video.path() if page.video else None
    ctx.close()
    data["video"] = str(pathlib.Path(video).relative_to(out)) if video else None
    return data


def trigger(e):
    if e["phase"] == "dwell" or e["phase"] == "load":
        return f"timed, {e['t']}s after load"
    if e["phase"] == "scroll":
        return f"on scroll, {e['scroll']}% down"
    return e["phase"]


def report(url, result):
    lines = [f"# Motion and popups: {url}", "",
             "What the page DOES, not what it looks like. Every row is something the swipe",
             "must rebuild, or drop with the operator's agreement. Each popup has a screenshot.", ""]
    for vp, d in result.items():
        lines += [f"## {vp}  (video: `{d['video']}`)", ""]
        lines += ["### Popups, bars and toasts that appear after load", ""]
        if d["events"]:
            lines += ["| # | kind | trigger | element | text |", "|---|---|---|---|---|"]
            for i, e in enumerate(d["events"]):
                lines.append(f"| {i} | {e['kind']} ({e['area']}% of screen) | {trigger(e)} | `{e['sel']}` | {e['text']} |")
        else:
            lines.append("None seen.")
        lines += ["", "### Animations (CSS keyframes, transitions, Web Animations)", ""]
        if d["anims"]:
            lines += ["| animation | element | duration | loops | first seen |", "|---|---|---|---|---|"]
            for a in d["anims"]:
                lines.append(f"| {a['name']} ({a['type']}) | `{a['sel']}` | {a['duration']} | {'forever' if a['infinite'] else 'once'} | {a['first']}s, {a['phase']} |")
        else:
            lines.append("None seen.")
        lines += ["", "### Regions moved by script (carousels, tickers, sticky reveals; one row per moving region)", ""]
        lines += [f"- `{m['sel']}`: {m['attr']} changed {m['n']}x, from {m['first']}s" for m in d["moves"]] or ["None seen."]
        lines += ["", "### Numbers that keep changing (countdowns, counters, stock)", ""]
        lines += [f"- `{c['sel']}`: changed {c['n']}x, e.g. \"{c['sample']}\"" for c in d["counters"]] or ["None seen."]
        lines.append("")
    return "\n".join(lines)


def compare(ref, cur):
    """Return what the reference had that this page lost, per viewport."""
    gaps = []
    for vp, r in ref.items():
        c = cur.get(vp, {})
        rk = sorted(f"{e['kind']} ({trigger(e).split(',')[0]})" for e in r["events"])
        ck = sorted(f"{e['kind']} ({trigger(e).split(',')[0]})" for e in c.get("events", []))
        for k in set(rk):
            if rk.count(k) > ck.count(k):
                gaps.append(f"{vp}: reference has {rk.count(k)}x {k}, this page has {ck.count(k)}")
        for key, label in (("anims", "animation(s)"), ("moves", "script-moved element(s)"), ("counters", "changing number(s)")):
            if len(r[key]) > len(c.get(key, [])):
                gaps.append(f"{vp}: reference has {len(r[key])} {label}, this page has {len(c.get(key, []))}")
    return gaps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="URL, or a local .html file")
    ap.add_argument("--out", default="motion")
    ap.add_argument("--dwell", type=int, default=25, help="seconds to wait for timed popups")
    ap.add_argument("--viewports", default="mobile,desktop")
    ap.add_argument("--compare", help="a reference motion.json to diff against")
    a = ap.parse_args()

    url = a.target if re.match(r"https?://", a.target) else pathlib.Path(a.target).resolve().as_uri()
    out = pathlib.Path(a.out).resolve()   # the video path is absolute; relative_to() needs both sides absolute
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp in a.viewports.split(","):
            result[vp] = watch(browser, url, vp, out, a.dwell)
        browser.close()
    (out / "motion.json").write_text(json.dumps(result, indent=2))
    (out / "MOTION.md").write_text(report(url, result))
    for vp, d in result.items():
        print(f"{vp}: {len(d['events'])} popup/bar/toast, {len(d['anims'])} animations, "
              f"{len(d['moves'])} script-moved, {len(d['counters'])} changing numbers")
    print(f"wrote {out}/MOTION.md")
    if a.compare:
        gaps = compare(json.loads(pathlib.Path(a.compare).read_text()), result)
        if gaps:
            print("\nMISSING vs reference:\n  " + "\n  ".join(gaps))
            sys.exit(1)
        print("\nparity: nothing the reference does is missing")


if __name__ == "__main__":
    main()
