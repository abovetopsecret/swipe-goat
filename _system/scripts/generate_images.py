#!/usr/bin/env python3
"""Drive image-manifest.json: generate each image, optimize, update status.

Model-agnostic. The actual image call lives in `generate_one()` — the default
implementation writes a labeled placeholder and marks the entry 'pending'. A Codex
session wires its own image tool there (or replaces this script entirely).

Usage: python3 generate_images.py <swipe_dir> [--dry-run] [--force]
"""
import argparse, json, os, pathlib, re, shutil, struct, subprocess, sys, zlib

def _brand_context(swipe_dir):
    """Lock-in prompt and canonical product images from the brand that owns this swipe
    (<brand>/swipes/<name>/ -> <brand>/brand_info/)."""
    info = swipe_dir.resolve().parent.parent / "brand_info"
    lock = ""
    md = info / "brand.md"
    if md.exists():
        m = re.search(r"^## Image lock-in prompt\s*\n(.*?)(?=^## |\Z)", md.read_text(encoding="utf-8"), re.S | re.M)
        if m:
            lock = "\n".join(l for l in m.group(1).splitlines() if not l.startswith(">")).strip()
    assets = sorted(p for p in (info / "assets").glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")) \
        if (info / "assets").is_dir() else []
    return lock, assets


def _codex_ready():
    if os.environ.get("SWIPE_IMAGES") == "placeholder" or not shutil.which("codex"):
        return False
    r = subprocess.run(["codex", "login", "status"], capture_output=True, text=True)
    return r.returncode == 0 and "Logged in" in (r.stdout + r.stderr)


def generate_one(entry, out_path, swipe_dir=None):
    """Return True if a real image was produced; False -> placeholder fallback.

    Uses the local `codex` CLI when it is installed and logged in, the same call the
    control panel makes: the reference slot art and the brand's canonical product
    images are attached, and Codex replies with the path of what it generated. Set
    SWIPE_IMAGES=placeholder to skip generation."""
    if swipe_dir is None or not _codex_ready():
        return False
    lock, assets = _brand_context(swipe_dir)
    ref = None
    for key in ("reference_crop", "src_local", "src_original"):
        v = entry.get(key) or ""
        cand = (swipe_dir / v) if v and not re.match(r"(https?:|data:)", v) else None
        if cand and cand.is_file():
            ref = cand
            break
    attach = ([ref] if ref else []) + assets
    size = f"{entry['width']}x{entry['height']}" if entry.get("width") and entry.get("height") else entry.get("aspect", "the slot aspect")
    parts = []
    if lock:
        parts.append(f"BRAND LOCK-IN (applies to every image):\n{lock}")
    parts.append(f"SLOT PROMPT ({entry.get('id')}, role {entry.get('role', 'content')}):\n{entry.get('prompt') or entry.get('brand_prompt', '')}")
    parts.append(
        "MECHANICS:\n"
        f"- Generate ONE image at {size} using your image generation tool.\n"
        + ("- The FIRST attached image is the reference slot art: keep its composition, framing and role; change only brand and product.\n" if ref else "")
        + f"- The {'other ' if ref else ''}attached image(s) are the brand's real product and logo: the product in your output must match them exactly.\n"
        "- No invented or garbled text, no fake logos, no watermark, no reference-brand marks.\n"
        "- Do NOT write any file into the workspace.\n"
        "- Your FINAL message must be ONLY the absolute filesystem path of the generated image file.")
    work = swipe_dir / ".swipe-goat" / "codex"
    work.mkdir(parents=True, exist_ok=True)
    last = work / f"{entry.get('id', 'img')}.out"
    args = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(swipe_dir),
            "--output-last-message", str(last)]
    for a in attach:
        args += ["-i", str(a)]
    args += ["--", "\n\n".join(parts)]   # -i is variadic: '--' keeps the prompt from being read as a file
    try:
        subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=int(os.environ.get("SWIPE_CODEX_TIMEOUT", "300")), check=True)
        reply = last.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"  codex failed for {entry.get('id')}: {str(e)[:160]}")
        return False
    m = re.search(r"(?:^|[\"'\s(])(/[^\s\"')]+\.(?:png|jpe?g|webp))", reply, re.I)
    src = pathlib.Path(m.group(1)) if m else None
    if not src or not src.is_file():
        print(f"  codex gave no usable image for {entry.get('id')}: {reply[:120]}")
        return False
    # Codex answers in PNG whatever the slot says; a PNG named .jpg renders, but
    # at several times the size and with the wrong type on the server. Re-encode to
    # the slot's own format when Pillow is here.
    try:
        from PIL import Image
        im = Image.open(src)
        fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP", ".png": "PNG"}.get(out_path.suffix.lower(), "PNG")
        if fmt == "JPEG":
            im = im.convert("RGB")
        im.save(out_path, fmt, **({"quality": 86} if fmt in ("JPEG", "WEBP") else {}))
    except ImportError:
        shutil.copyfile(src, out_path)
    return True

def _solid_png(w, h, rgb=(230, 224, 233)):
    """A valid solid-color PNG at the entry's aspect, capped small (stdlib only)."""
    cap = 160
    s = min(1.0, cap / max(w, h))
    pw, ph = max(1, round(w * s)), max(1, round(h * s))
    raw = (b"\x00" + bytes(rgb) * pw) * ph          # each row: filter byte 0 + pixels
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", pw, ph, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))

def placeholder(entry, out_path):
    """Write a labeled placeholder to out_path (keeps its filename so the HTML ref and
    the audit's existence check still resolve). Uses Pillow if present, else stdlib PNG."""
    w = int(entry.get("width") or 1200); h = int(entry.get("height") or 900)
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (w, h), (230, 224, 233))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w-1, h-1], outline=(120, 90, 130), width=4)
        d.text((20, 20), f"PENDING\n{entry.get('slot','')}", fill=(80, 50, 90))
        im.save(out_path)
    except ImportError:
        out_path.write_bytes(_solid_png(w, h))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("swipe_dir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--concurrency", type=int, default=2, help="codex generations at a time")
    a = ap.parse_args()

    sd = pathlib.Path(a.swipe_dir)
    man_path = sd / "image-manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    images = sd / "images"; images.mkdir(exist_ok=True)

    todo = [e for e in man.get("images", []) if not a.dry_run and (a.force or not (
        (images / e["target_filename"]).exists() and e.get("status") in ("done", "generated")))]
    if todo and _codex_ready():
        print(f"generating {len(todo)} image(s) with codex, {a.concurrency} at a time")

    def one(e):
        out = images / e["target_filename"]
        if generate_one(e, out, sd):
            e["status"] = "generated"   # a human still looks before it is 'done' (CODEX-IMAGES.md)
            print(f"  generated {e['target_filename']}")
        else:
            placeholder(e, out); e["status"] = "pending"

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as pool:
        list(pool.map(one, todo))
    pending = sum(1 for e in man.get("images", []) if e.get("status") == "pending")

    if not a.dry_run:
        man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"manifest ok: {len(man.get('images', []))} images, {pending} pending"
          + (" (dry-run)" if a.dry_run else ""))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
