#!/usr/bin/env python3
"""Externalize base64 raster image data URIs from a swipe HTML page.

Fonts are intentionally ignored. Raster images are decoded, normalized to PNG,
written under the page's images/ directory, and replaced in-place with
images/<prefix>-NN.png.
"""
import argparse
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image


RASTER = "webp|avif|png|jpeg|jpg|gif|x-icon|svg\\+xml"
DATA_RE = re.compile(
    r"data:image/(%s);base64,([A-Za-z0-9+/=\s]+?)(?=[\"')\s>&])" % RASTER,
    re.I,
)


def aspect(w, h):
    if not w or not h:
        return ""
    a, b = w, h
    while b:
        a, b = b, a % b
    return f"{w // a}:{h // a}"


def load_manifest(path, reference, brand):
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("reference", reference)
    data.setdefault("brand", brand)
    data.setdefault("images", [])
    if not isinstance(data["images"], list):
        data["images"] = []
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--reference", default="")
    ap.add_argument("--brand", default="")
    ap.add_argument("--start", type=int, default=1)
    args = ap.parse_args()

    page = Path(args.page)
    html = page.read_text(encoding="utf-8", errors="replace")
    images_dir = page.parent / "images"
    images_dir.mkdir(exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else page.parent / "image-manifest.json"
    manifest = load_manifest(manifest_path, args.reference, args.brand)
    existing_targets = {item.get("target_filename") for item in manifest["images"] if isinstance(item, dict)}

    index = args.start
    made = []

    def repl(match):
        nonlocal index
        raw_type = match.group(1).lower()
        payload = re.sub(r"\s+", "", match.group(2))
        try:
            blob = base64.b64decode(payload, validate=False)
        except Exception:
            return match.group(0)

        if raw_type == "svg+xml":
            while True:
                filename = f"{args.prefix}-{index:02d}.svg"
                index += 1
                if filename not in existing_targets and not (images_dir / filename).exists():
                    break
            out = images_dir / filename
            out.write_bytes(blob)
            manifest["images"].append(
                {
                    "id": f"{args.prefix}-{index - 1:02d}",
                    "slot": f"{args.prefix}-externalized-svg-{index - 1:02d}",
                    "role": "logo-or-icon",
                    "alt": "",
                    "width": 0,
                    "height": 0,
                    "aspect": "",
                    "src_original": f"data:image/{raw_type};base64",
                    "brand_prompt": "Externalized reference SVG. Replace with brand logo/icon asset if this slot remains in the final swipe.",
                    "target_filename": filename,
                    "status": "pending",
                }
            )
            existing_targets.add(filename)
            made.append((filename, 0, 0))
            return f"images/{filename}"

        try:
            im = Image.open(io.BytesIO(blob))
            im.load()
        except Exception:
            return match.group(0)

        if getattr(im, "is_animated", False):
            im.seek(0)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")

        while True:
            filename = f"{args.prefix}-{index:02d}.png"
            index += 1
            if filename not in existing_targets and not (images_dir / filename).exists():
                break

        out = images_dir / filename
        im.save(out, "PNG", optimize=True)
        w, h = im.size
        manifest["images"].append(
            {
                "id": f"{args.prefix}-{index - 1:02d}",
                "slot": f"{args.prefix}-externalized-raster-{index - 1:02d}",
                "role": "content",
                "alt": "",
                "width": w,
                "height": h,
                "aspect": aspect(w, h),
                "src_original": f"data:image/{raw_type};base64",
                "brand_prompt": "Externalized reference raster. Replace with brand-safe generated image or real asset if this slot remains in the final swipe.",
                "target_filename": filename,
                "status": "pending",
            }
        )
        existing_targets.add(filename)
        made.append((filename, w, h))
        return f"images/{filename}"

    html2 = DATA_RE.sub(repl, html)
    page.write_text(html2, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"{page}: externalized {len(made)} raster image(s)")
    for filename, w, h in made[:80]:
        print(f"  {filename}: {w}x{h}")
    if len(made) > 80:
        print(f"  ... {len(made) - 80} more")
    print(f"base64 raster left: {len(DATA_RE.findall(html2))}")


if __name__ == "__main__":
    main()
