# Counterfeit-Detection Classifier — `classify.py`

A single-script v1 that consumes the brand profiles in `output/` and decides whether a given seller listing is **authorized**, **unauthorized**, or needs **review**.

## Quick start

```bash
# One-time setup (creates a venv with Pillow / ImageHash / requests):
python3 -m venv .venv
source .venv/bin/activate
pip install Pillow ImageHash requests

# One-time per brand: build the perceptual-hash index from products_full.json
python image_hash_index.py build --brand handson-gloves
python image_hash_index.py build --brand sherlock-holmes

# Discovery + classification (uses SerpAPI):
export SERPAPI_KEY=<your_key>
python classify.py --brand handson-gloves --discover --max 10

# Classify specific URLs:
python classify.py --brand handson-gloves --url https://www.amazon.com/dp/B0942X1K99

# Save verdicts to a file:
python classify.py --brand handson-gloves --discover --output verdicts.json
```

## Output shape

```json
{
  "brand": "handson-gloves",
  "candidates_checked": 10,
  "verdict_counts": {"authorized": 3, "unauthorized": 5, "review": 2},
  "verdicts": [
    {
      "seller_host": "amazon.com",
      "url": "https://www.amazon.com/...",
      "verdict": "authorized",
      "score": 85,
      "reasons": ["Amazon merchant ID A4L4GSX1OQUQL matches brand storefront"],
      "evidence": ["amazon_merchant=A4L4GSX1OQUQL"],
      "fetch_status": 200
    }
  ]
}
```

## How scoring works

Each signal contributes a weighted score. Final verdict:
- `score >= 50` → **authorized**
- `score <= -40` → **unauthorized**
- otherwise → **review**

| Signal | Weight |
|---|---|
| Whitelist domain exact match | +90 |
| Whitelist domain subdomain match | +70 |
| Amazon merchant-ID match against brand storefront | +85 |
| High-confidence authorized reseller | +60 |
| Claimed-but-unverified reseller | +30 |
| **Image phash strong match (Hamming ≤ 6)** | **-85** |
| **Image phash weak match (Hamming ≤ 10)** | **-45** |
| Image URL hot-linked from brand CDN (exact-URL) | -75 |
| Distinctive brand phrase (per phrase) | -35 |
| Tagline misuse ("Most Imitated, Never Duplicated") | -50 (additive) |
| Brand SKU prefix in HTML | -40 |
| Price below brand floor (HandsOn $19.99) | -25 |
| Authority-claim language ("patented", "#1 Ranked", "Official Site") on non-whitelisted seller | -20 |
| Brand name on a non-whitelisted seller | -15 |

**Whitelist short-circuit:** if the seller is on a whitelisted domain or matches the brand's Amazon merchant ID, the verdict is `authorized` and negative signals are skipped (those signals are *expected* on the brand's own pages — they're how we recognize the brand's content).

Weights are in the `WEIGHTS` dict at the top of `classify.py` — tune as needed.

## Inputs the script reads

- `output/{brand}_profile.json` — required
- `output/{brand}_whitelist.json` — optional (used for Sherlock Holmes)
- `memory/BRAND_PROFILES/{brand}/raw_artifacts/products_full.json` — optional (loads brand-CDN image URLs for exact hotlink detection)
- `memory/BRAND_PROFILES/{brand}/image_index.json` — optional (perceptual-hash index, built by `image_hash_index.py build --brand <slug>`)

## Perceptual image hashing — `image_hash_index.py`

Builds a pHash + dHash index of the brand's product images so the classifier can detect counterfeits that **rehost** the brand's photos under a different URL (the dominant fake pattern).

```bash
# Build the index (downloads each image, computes 64-bit phash + dhash)
python image_hash_index.py build --brand handson-gloves
# → wrote memory/BRAND_PROFILES/handson-gloves/image_index.json (32 entries)

# Match a candidate image against the index
python image_hash_index.py match --brand handson-gloves --url https://example.com/some.jpg
```

When `classify.py` runs, it auto-loads the index if it exists, parses up to 4 image URLs from each candidate listing's HTML, and adds the `image_phash_strong` (-85) or `image_phash_weak` (-45) signal if any match.

Distance thresholds (out of 64): strong ≤ 6, weak ≤ 10. Tunable in `MATCH_THRESHOLDS` at the top of `image_hash_index.py`.

## Dependencies

- `requests` (only third-party dep)
- Python 3.10+

```bash
pip install requests
```

## Known limitations of v1

1. **Image hashing is exact-URL only** (not perceptual). True counterfeit-image detection needs `imagehash`/`opencv` and a side index of brand image phashes. Add later.
2. **JS-rendered marketplace pages** (Amazon, eBay) often hide details behind JS — `requests`-only fetch may get a stub. For Amazon especially, pair with the Chrome MCP browser or a Playwright pass.
3. **Discovery queries are static** per brand. Tune `discover_candidates()` to adjust the SerpAPI query set.
4. **Price-floor extraction** is a naive regex; misses non-USD currencies and ranges.
5. **No persistence** — every run is fresh. For a continuous monitor, wrap in a cron job that diffs against prior verdicts.

## When to upgrade

If the false-positive rate on `unauthorized` verdicts exceeds ~10% on real data, the next steps are:
1. Add perceptual image hashing (phash / dhash) — biggest single accuracy gain.
2. Replace `requests` fetch with a headless-browser fetch for JS-heavy pages.
3. Add a small allowlist override file for "known-OK third parties" you discover empirically.
