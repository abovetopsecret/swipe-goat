#!/usr/bin/env python3
"""Resize/compress an image for web (<=1200px longest edge). Needs Pillow.

Usage: python3 optimize.py <img> [more imgs...]   (edits in place)
If Pillow is missing, prints a skip notice and exits 0 (non-fatal).
"""
import sys, pathlib
try:
    from PIL import Image
except ImportError:
    print("optimize.py: Pillow not installed; skipping (Codex can optimize another way).")
    raise SystemExit(0)

MAX = 1200
def optimize(p: pathlib.Path):
    im = Image.open(p)
    w, h = im.size
    scale = min(1.0, MAX / max(w, h))
    if scale < 1.0:
        im = im.resize((round(w*scale), round(h*scale)), Image.LANCZOS)
    if p.suffix.lower() in (".jpg", ".jpeg"):
        im.convert("RGB").save(p, "JPEG", quality=82, optimize=True)
    elif p.suffix.lower() == ".png":
        im.save(p, optimize=True)
    else:
        im.save(p)
    print(f"  optimized {p.name}: {im.size[0]}x{im.size[1]}")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        optimize(pathlib.Path(arg))
