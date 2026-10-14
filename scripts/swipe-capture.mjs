#!/usr/bin/env node
// Step 0 of the runbook, from a URL: capture the reference, gate it, scaffold the
// swipe folder. Everything after this is RUNBOOK.md unchanged.
//
//   node swipe-capture.mjs <url> [--brand <dir>] [--name <folder>]
//
// The capture has to be a FULLY SELF-CONTAINED single file. A capture that still
// points at external scripts does not hydrate when opened as a static file, it
// renders glitchy, and a glitchy base is what tempts the rebuild the prime
// directive exists to prevent. So the gate runs here, automatically, rather than
// being a grep in a checklist that gets skipped.
import { existsSync, mkdirSync, readFileSync, cpSync, statSync, readdirSync } from 'node:fs';
import { join, resolve, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const url = args.find((a) => /^https?:\/\//.test(a));
const opt = (name) => { const i = args.indexOf('--' + name); return i < 0 ? null : args[i + 1]; };
if (!url) {
  console.error('usage: swipe-capture.mjs <url> [--brand <dir>] [--name <folder>]');
  process.exit(2);
}

// ROOT is the nearest ancestor holding _system/, same rule the runbook gives the
// operator, so a workspace's own engine wins. Without one, use the engine this
// plugin ships: a fresh install has no workspace yet and must still run.
const PLUGIN = join(HERE, '..');
let root = resolve(opt('brand') || process.cwd());
while (!existsSync(join(root, '_system')) && dirname(root) !== root) root = dirname(root);
if (!existsSync(join(root, '_system'))) root = PLUGIN;
// The brand dir is the one holding brand_info/. cwd when that is a brand dir,
// otherwise the operator has to say which brand this swipe is for.
const brandDir = resolve(opt('brand') || process.cwd());
if (!existsSync(join(brandDir, 'brand_info'))) {
  const parent = existsSync(join(brandDir, '..')) ? join(brandDir, '..') : process.cwd();
  const brands = readdirSync(parent).filter((b) => existsSync(join(parent, b, 'brand_info')));
  console.error(`not a brand dir (no brand_info/): ${brandDir}`);
  console.error(brands.length ? `pass --brand <dir>, one of: ${brands.join(', ')}`
    : 'no brand dirs here: make <brand>/brand_info/brand.md from _system/templates/brand.md.template');
  process.exit(2);
}

// Slug from the URL path, falling back to the host. A funnel URL's last path
// segment is the offer name, which is what you want the folder called.
const u = new URL(url);
const seg = u.pathname.split('/').filter(Boolean).pop() || '';
const slugify = (s) => s.toLowerCase().replace(/\.[a-z]{2,5}$/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const slug = slugify(/^(index|home|default)$/.test(seg) || !seg ? u.hostname.replace(/^www\./, '') : seg).slice(0, 48);
const date = new Date().toISOString().slice(0, 10);
let folder = opt('name') || `${slug}-${basename(brandDir)}-${date}`;
for (let n = 2; existsSync(join(brandDir, 'swipes', folder)); n++) {
  if (opt('name')) break;                       // an explicitly named folder is reused on purpose
  folder = `${slug}-${basename(brandDir)}-${date}-${n}`;
}
const dir = join(brandDir, 'swipes', folder);
mkdirSync(dir, { recursive: true });
const ref = join(dir, `${slug}.html`);

// Installed as a Claude Code plugin, this arrives as source with no node_modules
// and no browser binary. Rather than make that a README step that gets skipped,
// do it once on first run.
if (!existsSync(join(PLUGIN, 'node_modules'))) {
  console.error('first run: installing singlefile, playwright and chromium (a few minutes, once)');
  execFileSync('npm', ['install', '--no-audit', '--no-fund'], { cwd: PLUGIN, stdio: 'inherit' });
  execFileSync('npx', ['playwright', 'install', 'chromium'], { cwd: PLUGIN, stdio: 'inherit' });
}

// SingleFile needs a browser. Playwright's chromium is already a dependency here,
// so prefer it over the user's own Chrome: a separate binary means no profile,
// no extensions, no logged-in session leaking into the capture.
function chromium() {
  const where = () => execFileSync(process.execPath, ['-e', "import('playwright').then(p=>process.stdout.write(p.chromium.executablePath()))"],
    { cwd: PLUGIN, encoding: 'utf8' }).trim();
  try {
    let path = where();
    // node_modules can be present while the browser is not: every Playwright
    // upgrade pins a new Chromium build, and the old one does not satisfy it.
    if (!existsSync(path)) {
      console.error(`chromium build missing (${path.split('/ms-playwright/')[1]?.split('/')[0] || path}): installing it once`);
      execFileSync('npx', ['playwright', 'install', 'chromium'], { cwd: PLUGIN, stdio: 'inherit' });
      path = where();
    }
    return path;
  } catch {
    const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
    if (existsSync(chrome)) return chrome;
    console.error('no chromium: run `npx playwright install chromium` in the repo');
    process.exit(2);
  }
}

console.log(`capturing ${url}\n  -> ${ref}`);
// Deferred/lazy content is handled by SingleFile itself (--load-deferred-content
// is on by default and dispatches scroll), so there is no scrolling to do here.
// Scripts stay blocked (the default): a frozen static base carries none of the
// reference's analytics calls, which would be live-reference-URL leaks under
// hard rule 4. Step 4 restores the JS the swipe actually needs.
execFileSync('npx', ['single-file', url, ref,
  `--browser-executable-path=${chromium()}`,
  // Heavy pages crash the renderer while inlining: the whole page data crosses
  // the CDP bridge in one value. Capping resource size is what makes a 3 MB PDP
  // capture at all, and images get replaced in step 1 regardless.
  '--max-resource-size-enabled', '--max-resource-size=1',
  '--browser-wait-until=networkIdle',
  '--browser-load-max-time=90000',
  '--browser-capture-max-time=90000',
], { cwd: PLUGIN, stdio: 'inherit' });

if (!existsSync(ref)) { console.error('capture produced no file'); process.exit(1); }
const html = readFileSync(ref, 'utf8');
const count = (re) => (html.match(re) || []).length;
const extScripts = count(/<script[^>]*\bsrc=/gi);
const extSheets = count(/<link[^>]*rel=["']?stylesheet/gi);
const b64 = count(/data:image\/[^;]*;base64/gi);

// A page that hard-blocks headless, or sits behind a login, captures as a shell:
// the gate above passes it (a shell has no external deps either) and you find out
// four steps later. Measure the text instead.
const text = html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const size = statSync(ref).size;

console.log(`\ncapture-quality gate (${size < 1e6 ? Math.round(size / 1e3) + ' KB' : (size / 1e6).toFixed(1) + ' MB'})`);
console.log(`  external <script src>      ${extScripts}  (must be 0)`);
console.log(`  external stylesheet links  ${extSheets}  (must be 0)`);
console.log(`  base64 images              ${b64}  (externalize in step 1)`);
console.log(`  visible text               ${text.length} chars`);
if (text.length < 1200) {
  console.error('\nGATE FAILED: that is a shell, not a funnel. The page is behind a login,');
  console.error('or it blocks headless. Capture it with the SingleFile browser extension in');
  console.error('your own signed-in Chrome and drop the file in the swipe folder instead.');
  process.exit(1);
}
// A capture takes the DOM as it stands, so anything behind a closed accordion
// comes through as an empty panel: the FAQ answers, the Description, and on a
// personalised PDP the whole preview widget. There is no fix inside SingleFile
// (its single-file-on-before-capture hook does not fire under the CLI, and a
// timed expand injected with --browser-script does not survive either, both
// verified). Recover that copy from the reader capture, which does expand.
const collapsed = (html.match(/aria-expanded=["']false["']/gi) || []).length
                + (html.match(/<details(?![^>]*\bopen\b)/gi) || []).length;
if (collapsed) {
  console.log(`  collapsed panels            ${collapsed}  (their contents are NOT in this file)`);
  console.log('  -> run capture.mjs on the same URL and read copy.md for what is behind them');
}

if (extScripts || extSheets) {
  console.error('\nGATE FAILED: the capture is not self-contained and will render glitchy.');
  console.error('Re-capture with the SingleFile browser extension and use that file instead.');
  console.error('Do NOT rebuild from it.');
  process.exit(1);
}

// Shots of the LIVE page, for the "eyeball the capture against the live page"
// check. Without them that comparison happens from memory, or not at all.
try {
  const { chromium: pw, devices } = await import('playwright');
  const browser = await pw.launch();
  for (const [label, ctxOpts] of [['desktop', { viewport: { width: 1440, height: 900 } }], ['mobile', devices['iPhone 13']]]) {
    const page = await (await browser.newContext(ctxOpts)).newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => page.goto(url, { timeout: 60000 }));
    await page.evaluate(async () => {
      const step = Math.round(innerHeight * 0.8);
      for (let y = 0; y < document.body.scrollHeight + step; y += step) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 250)); }
      scrollTo(0, 0); await new Promise((r) => setTimeout(r, 600));
    });
    await page.screenshot({ path: join(dir, `live-${label}.png`), fullPage: true });
    console.log(`  wrote live-${label}.png`);
  }
  await browser.close();
} catch (e) {
  console.log('  (live screenshots skipped:', e.message.split('\n')[0] + ')');
}

// Motion and popups (hard rule 7). Watched on the LIVE url, because the capture
// above has already lost every popup that was not on screen and every script
// that moved something. Python, like the rest of the engine; its Playwright is
// installed once here the same way the Node side is above.
const motion = join(root, '_system/scripts/motion.py');
if (existsSync(motion)) {
  const py = process.env.PYTHON || 'python3';
  try {
    execFileSync(py, ['-c', 'import playwright.sync_api'], { stdio: 'ignore' });
  } catch {
    console.error('first run: installing Python Playwright for the motion inventory (once)');
    execFileSync(py, ['-m', 'pip', 'install', '--user', '--quiet', 'playwright'], { stdio: 'inherit' });
    execFileSync(py, ['-m', 'playwright', 'install', 'chromium'], { stdio: 'inherit' });
  }
  console.log('\nwatching the live page for animations and popups (about a minute)');
  try {
    execFileSync(py, [motion, url, '--out', join(dir, '.swipe-goat', 'motion')], { stdio: 'inherit' });
  } catch (e) {
    console.error('  motion inventory failed; run it by hand before step 0b:', e.message.split('\n')[0]);
  }
}

// Per-swipe scaffold: SWIPE.md, image-manifest.json, DELIVERY.md, images/.
const tpl = join(root, '_system/templates/swipe-folder');
if (existsSync(tpl)) {
  for (const f of ['SWIPE.md', 'image-manifest.json', 'DELIVERY.md', 'images']) {
    const dst = join(dir, f);
    if (!existsSync(dst) && existsSync(join(tpl, f))) cpSync(join(tpl, f), dst, { recursive: true });
  }
  console.log('  scaffolded SWIPE.md, image-manifest.json, DELIVERY.md, images/');
}

console.log(`\nGATE PASSED. Reference of record: ${ref}`);
console.log(`Next: open it, compare against live-desktop.png, read .swipe-goat/motion/MOTION.md,`);
console.log(`then follow ${join(root, '_system/RUNBOOK.md')}`);
console.log(`from step 0's cp onward (cp the reference to its role name and edit IN PLACE).`);
