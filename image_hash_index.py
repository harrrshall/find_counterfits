#!/usr/bin/env python3
"""
Build and use a perceptual-hash (phash) index of a brand's product images.

Two modes:

  build   Download each image from the brand's products_full.json,
          compute pHash + dHash, save to memory/BRAND_PROFILES/{slug}/image_index.json

  match   Given an image URL, fetch it, compute pHash, find nearest brand image
          (Hamming distance ≤ threshold). Used by classify.py.

CLI:
  python image_hash_index.py build --brand handson-gloves
  python image_hash_index.py match --brand handson-gloves --url <image_url>

The index file format:

  {
    "brand": "handson-gloves",
    "built_at": "...",
    "hash_size": 8,
    "entries": [
      {"src": "<url>", "phash": "<hex>", "dhash": "<hex>",
       "product_handle": "...", "product_title": "..."}
    ]
  }

Hamming distance ≤ 6 (out of 64 bits) is treated as a strong match;
≤ 10 is a weak match. Tune in `MATCH_THRESHOLDS`.
"""

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imagehash
import requests
from PIL import Image, UnidentifiedImageError

HASH_SIZE = 8  # 8x8 = 64-bit hashes
MATCH_THRESHOLDS = {"strong": 6, "weak": 10}
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
FETCH_TIMEOUT = 15
PROJECT_ROOT = Path(__file__).resolve().parent


def fetch_image(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
        img.load()
        return img.convert("RGB")
    except (requests.RequestException, UnidentifiedImageError, OSError) as e:
        sys.stderr.write(f"[skip] {url} :: {e}\n")
        return None


def hash_image(img: Image.Image) -> tuple[str, str]:
    return (
        str(imagehash.phash(img, hash_size=HASH_SIZE)),
        str(imagehash.dhash(img, hash_size=HASH_SIZE)),
    )


def index_path(brand_slug: str) -> Path:
    return (
        PROJECT_ROOT
        / "memory"
        / "BRAND_PROFILES"
        / brand_slug
        / "image_index.json"
    )


def load_brand_images(brand_slug: str) -> list[dict]:
    raw_path = (
        PROJECT_ROOT
        / "memory"
        / "BRAND_PROFILES"
        / brand_slug
        / "raw_artifacts"
        / "products_full.json"
    )
    if not raw_path.exists():
        sys.exit(f"raw artifacts not found: {raw_path}")
    raw = json.loads(raw_path.read_text())
    out: list[dict] = []
    for p in raw.get("products", []) or []:
        for img in p.get("images", []) or []:
            src = img.get("src")
            if not src:
                continue
            out.append(
                {
                    "src": src,
                    "product_handle": p.get("handle"),
                    "product_title": p.get("title"),
                }
            )
    return out


def cmd_build(args) -> None:
    items = load_brand_images(args.brand)
    sys.stderr.write(f"[build] {len(items)} images to hash for {args.brand}\n")

    entries: list[dict] = []
    for i, item in enumerate(items, 1):
        img = fetch_image(item["src"])
        if not img:
            continue
        phash, dhash = hash_image(img)
        entries.append({**item, "phash": phash, "dhash": dhash})
        if i % 5 == 0 or i == len(items):
            sys.stderr.write(f"  {i}/{len(items)} hashed\n")
        time.sleep(0.05)

    index = {
        "brand": args.brand,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "hash_size": HASH_SIZE,
        "match_thresholds": MATCH_THRESHOLDS,
        "entries": entries,
    }
    out = index_path(args.brand)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2))
    print(f"wrote {out} ({len(entries)} entries)")


def hamming(a: str, b: str) -> int:
    """Hamming distance between two hex-encoded ImageHash strings."""
    return int(imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b))


def find_matches(
    candidate_phash: str, candidate_dhash: str, index: dict, threshold: int = MATCH_THRESHOLDS["weak"]
) -> list[dict]:
    """Return matching brand entries sorted by combined distance, only those <= threshold."""
    out: list[dict] = []
    for e in index.get("entries", []):
        try:
            dp = hamming(candidate_phash, e["phash"])
            dd = hamming(candidate_dhash, e["dhash"])
        except (ValueError, KeyError):
            continue
        combined = min(dp, dd)  # nearest of the two
        if combined <= threshold:
            out.append({**e, "phash_dist": dp, "dhash_dist": dd, "min_dist": combined})
    out.sort(key=lambda x: x["min_dist"])
    return out


def cmd_match(args) -> None:
    idx_path = index_path(args.brand)
    if not idx_path.exists():
        sys.exit(f"index not found; run: python {sys.argv[0]} build --brand {args.brand}")
    index = json.loads(idx_path.read_text())

    img = fetch_image(args.url)
    if not img:
        sys.exit("could not fetch/decode candidate image")
    cph, cdh = hash_image(img)

    matches = find_matches(cph, cdh, index, threshold=args.threshold)
    print(
        json.dumps(
            {
                "brand": args.brand,
                "candidate_url": args.url,
                "candidate_phash": cph,
                "candidate_dhash": cdh,
                "threshold": args.threshold,
                "matches": matches[:10],
                "best": matches[0] if matches else None,
            },
            indent=2,
        )
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build the brand image hash index")
    b.add_argument("--brand", required=True)
    b.set_defaults(func=cmd_build)

    m = sub.add_parser("match", help="match a candidate image URL against the index")
    m.add_argument("--brand", required=True)
    m.add_argument("--url", required=True, help="candidate image URL")
    m.add_argument("--threshold", type=int, default=MATCH_THRESHOLDS["weak"])
    m.set_defaults(func=cmd_match)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
