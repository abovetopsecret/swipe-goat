#!/usr/bin/env node
// Capture a funnel page as it actually renders, and write a spec you can build from.
//
// A page like this is PageFly or Shopify sections plus a personalisation script,
// so the served HTML is close to empty and curl tells you nothing. Everything
// worth having only exists after JS has run, after lazy sections have mounted,
// and with the accordions open.
//
//   node capture.mjs <url> <outdir>
//
// Needs chromium once:  npx playwright install chromium
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

// Installed as a Claude Code plugin, this arrives as source with no node_modules
// and no browser binary. Rather than make that a README step that gets skipped,
// do it once on first run.
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
async function playwright() {
  try {
    return await import('playwright');
  } catch {
    console.error('first run: installing playwright and chromium (a few minutes, once)');
    const run = (cmd, args) => execFileSync(cmd, args, { cwd: ROOT, stdio: 'inherit' });
    run('npm', ['install', '--no-audit', '--no-fund']);
    run('npx', ['playwright', 'install', 'chromium']);
    return import('playwright');
  }
}
const { chromium, devices } = await playwright();

const [url, outdir] = process.argv.slice(2);
if (!url || !outdir) {
  console.error('usage: capture.mjs <url> <outdir>');
  process.exit(2);
}
mkdirSync(outdir, { recursive: true });
const write = (name, data) => {
  writeFileSync(join(outdir, name), typeof data === 'string' ? data : JSON.stringify(data, null, 2));
  console.log('  wrote', name);
};

// Scroll the whole page in steps and wait. Intersection-observer sections do not
// exist in the DOM until they have been near the viewport, so a capture taken at
// the top of the page silently misses most of the funnel.
async function settle(page) {
  await page.evaluate(async () => {
    const step = Math.round(window.innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight + step; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 300));
    }
    window.scrollTo(0, 0);
    await new Promise((r) => setTimeout(r, 800));
  });
}

// Open every accordion. The FAQ and the "Description" panel are usually where the
// specifics live (sizes, materials, turnaround), and they are collapsed by default.
async function expand(page) {
  return page.evaluate(async () => {
    let opened = 0;
    for (const d of document.querySelectorAll('details:not([open])')) { d.open = true; opened++; }
    const clickable = [...document.querySelectorAll('button,summary,[role="button"],[aria-expanded]')];
    for (const el of clickable) {
      // An anchor is navigation by definition, and a bare <button> inside a form
      // defaults to type=submit. Clicking either tears down the execution context
      // mid-capture, which is how the first run of this died.
      if (el.tagName === 'A' || el.closest('a')) continue;
      if (el.tagName === 'BUTTON' && el.closest('form') && el.type !== 'button') continue;
      const expanded = el.getAttribute('aria-expanded');
      const looksCollapsed = expanded === 'false' || /[+▸▾⌄]\s*$/.test(el.innerText || '');
      // never click anything that buys, submits or navigates away
      const dangerous = /add to cart|buy|checkout|subscribe|submit|sign up|accept|agree/i.test(el.innerText || '');
      if (looksCollapsed && !dangerous) { try { el.click(); opened++; } catch {} }
    }
    await new Promise((r) => setTimeout(r, 900));
    return opened;
  });
}

// The ordered skeleton: what a visitor meets, top to bottom.
const OUTLINE = () => {
  const out = [];
  const seen = new Set();
  const walk = (el) => {
    for (const n of el.children) {
      if (/^(SCRIPT|STYLE|NOSCRIPT|SVG|IFRAME)$/.test(n.tagName)) continue;
      const text = (n.innerText || '').trim().replace(/\s+/g, ' ');
      if (/^H[1-6]$/.test(n.tagName) && text) {
        const key = n.tagName + text;
        if (!seen.has(key)) { seen.add(key); out.push({ kind: n.tagName, text: text.slice(0, 160) }); }
      } else if ((n.tagName === 'BUTTON' || n.tagName === 'A') && text && text.length < 60) {
        const cls = typeof n.className === 'string' ? n.className : '';
        if (n.tagName === 'BUTTON' || /btn|button|cta/i.test(cls)) {
          const key = 'B' + text;
          if (!seen.has(key)) { seen.add(key); out.push({ kind: 'BUTTON', text }); }
        }
      }
      walk(n);
    }
  };
  walk(document.body);
  return out;
};

// The numbers you cannot eyeball: the type ramp, the palette, the spacing scale.
// These are what make a rebuild land in one pass instead of five.
const TOKENS = () => {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const sample = (sel, limit = 6) =>
    [...document.querySelectorAll(sel)].slice(0, limit).map((e) => {
      const c = getComputedStyle(e);
      return {
        text: (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 44),
        font: c.fontFamily.split(',')[0].replace(/["']/g, ''),
        size: px(c.fontSize), weight: c.fontWeight, lineHeight: c.lineHeight,
        color: c.color, letterSpacing: c.letterSpacing,
      };
    });
  const buttons = [...document.querySelectorAll('button,a')]
    .filter((b) => { const c = getComputedStyle(b); return c.backgroundColor !== 'rgba(0, 0, 0, 0)' && (b.innerText || '').trim(); })
    .slice(0, 6)
    .map((b) => {
      const c = getComputedStyle(b);
      return {
        text: b.innerText.trim().slice(0, 36), bg: c.backgroundColor, color: c.color,
        radius: c.borderRadius, padding: c.padding, size: px(c.fontSize), weight: c.fontWeight,
      };
    });
  // vertical rhythm: how much air each top-level block is given
  const blocks = [...document.body.querySelectorAll('section, [id*="section"], [class*="section"]')]
    .filter((e) => e.getBoundingClientRect().height > 120)
    .slice(0, 14)
    .map((e) => {
      const c = getComputedStyle(e);
      return { id: e.id || (typeof e.className === 'string' ? e.className.split(' ')[0] : ''), paddingTop: px(c.paddingTop), paddingBottom: px(c.paddingBottom), bg: c.backgroundColor };
    });
  return {
    h1: sample('h1', 2), h2: sample('h2'), h3: sample('h3'), body: sample('p'),
    buttons, blocks,
    pageBackground: getComputedStyle(document.body).backgroundColor,
    bodyFont: getComputedStyle(document.body).fontFamily,
  };
};

// Copy, grouped under the heading it sits beneath, which is the form you actually
// rewrite from.
const COPY = () => {
  const heads = [...document.querySelectorAll('h1,h2')];
  return heads.map((h) => {
    let n = h;
    for (let i = 0; i < 6 && n.parentElement; i++) {
      n = n.parentElement;
      if ((n.innerText || '').length > (h.innerText || '').length + 80) break;
    }
    return {
      heading: h.innerText.trim().replace(/\s+/g, ' '),
      body: (n.innerText || '').replace(/\s*\n\s*/g, '\n').trim().slice(0, 1800),
    };
  });
};

const ASSETS = () =>
  [...document.querySelectorAll('img')]
    .filter((i) => i.naturalWidth > 200)
    .slice(0, 60)
    .map((i) => ({ src: i.currentSrc || i.src, w: i.naturalWidth, h: i.naturalHeight, alt: i.alt || '' }));

(async () => {
  const browser = await chromium.launch();
  try {
    for (const [label, ctxOpts] of [
      ['desktop', { viewport: { width: 1440, height: 900 } }],
      ['mobile', devices['iPhone 13']],
    ]) {
      const ctx = await browser.newContext(ctxOpts);
      const page = await ctx.newPage();
      console.log(`\n[${label}] ${url}`);
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => page.goto(url, { timeout: 60000 }));
      await settle(page);
      // A stray click can still navigate on a page that binds its own handlers.
      // Capturing the wrong page silently is worse than a noisy retry.
      const before = page.url();
      const opened = await expand(page).catch((e) => { console.log('  expand bailed:', e.message.split('\n')[0]); return 0; });
      if (page.url() !== before) {
        console.log('  a click navigated, going back');
        await page.goto(url, { timeout: 60000 });
        await settle(page);
      }
      console.log('  expanded', opened, 'collapsed blocks');
      await settle(page);

      await page.screenshot({ path: join(outdir, `${label}.png`), fullPage: true });
      console.log('  wrote', `${label}.png`);

      if (label === 'desktop') {
        write('rendered.html', await page.content());
        write('outline.json', await page.evaluate(OUTLINE));
        write('tokens.json', await page.evaluate(TOKENS));
        write('assets.json', await page.evaluate(ASSETS));
        const copy = await page.evaluate(COPY);
        write('copy.json', copy);
        write('copy.md', copy.map((c) => `## ${c.heading}\n\n${c.body}\n`).join('\n'));
      }
      await ctx.close();
    }
  } finally {
    await browser.close();
  }
  console.log(`\ncaptured to ${outdir}`);
})();
