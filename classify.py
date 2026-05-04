#!/usr/bin/env python3
"""
Counterfeit-detection classifier — single-script v1.

Reads a brand profile JSON + (for Sherlock Holmes) the whitelist JSON,
discovers candidate sellers via SerpAPI, and scores each as
AUTHORIZED / UNAUTHORIZED / REVIEW with reasons.

Usage:
  export SERPAPI_KEY=...
  python classify.py --brand handson-gloves --discover
  python classify.py --brand handson-gloves --url https://example.com/listing
  python classify.py --brand sherlock-holmes --discover --max 10
  python classify.py --brand handson-gloves --url <u1> --url <u2>

Inputs:
  --brand        slug, e.g. handson-gloves or sherlock-holmes (matches output/<slug>_profile.json)
  --url          one or more seller URLs to classify (repeatable)
  --discover     also run SerpAPI discovery for candidate sellers
  --max          max candidates from discovery (default 15)
  --output       output file path (default: stdout)
  --profile-dir  directory with profile JSONs (default: ./output)

Output: a JSON list of verdicts. Each verdict has:
  seller, url, verdict, score, reasons[], evidence[]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests


def _load_dotenv() -> None:
    """Tiny .env loader (no third-party dep). Only sets keys not already in env."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# ---------- Config ----------

SERPAPI_ENDPOINT = "https://serpapi.com/search"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
FETCH_TIMEOUT = 15

# Signal weights (out of 100). Positive = authorized, negative = unauthorized.
WEIGHTS = {
    "whitelist_domain_exact":      +90,
    "whitelist_domain_subdomain":  +70,
    "amazon_merchant_id_match":    +85,
    "authorized_reseller_high":    +60,
    "authorized_reseller_claimed": +30,
    "image_phash_strong":           -85,  # phash dist <= 6 (out of 64)
    "image_phash_weak":             -45,  # phash dist <= 10
    "image_url_exact_match":        -75,
    "distinctive_phrase":           -35,
    "sku_prefix_present":           -40,
    "price_below_floor":            -25,
    "patented_claim_language":      -20,
    "brand_name_in_title":          -15,  # only matters if no whitelist signal hit
    "tagline_misuse":               -50,
}

# Optional perceptual-hash signal — works only if image_hash_index has been built.
try:
    import image_hash_index as _IH

    _IH_AVAILABLE = True
except ImportError:
    _IH_AVAILABLE = False

MAX_IMAGES_TO_HASH_PER_PAGE = 4
PAGE_IMAGE_URL_RE = re.compile(
    r'(?i)(?:src|data-src|content)=["\'](https?://[^"\'\s]+\.(?:jpe?g|png|webp))',
)

DISTINCTIVE_PHRASES_BY_BRAND = {
    "sherlock-holmes": [
        "just deduce it",
        "your one-stop shop for all things sherlock",
        "from 221b to your doorstep",
        "elevate your detective style",
    ],
    "handson-gloves": [
        "most imitated, never duplicated",
        "scrubbing nodules on the fingers and palms",
        "just a simple flick of the wrist",
        "patented, first of its kind nodules",
    ],
}

PATENTED_CLAIM_PATTERNS = [
    r"\bpatented\b",
    r"\b#1 ranked\b",
    r"\baward[- ]winning\b",
    r"\bofficial\s+site\b",
]

SKU_PREFIX_BY_BRAND = {
    "handson-gloves": [r"\bHGLV\d", r"\bGARD\d", r"\bFNSH\d", r"\bHFP\d{4}"],
    "sherlock-holmes": [],  # this brand doesn't expose distinctive SKU prefixes in listings
}

PRICE_FLOOR_USD = {
    "handson-gloves": 19.99,
    "sherlock-holmes": None,  # multi-currency, no single floor
}

# ---------- Utility ----------


def hostname(u: str) -> str:
    try:
        h = urllib.parse.urlparse(u).hostname or ""
        return h.lower()
    except Exception:
        return ""


def host_matches(host: str, candidate: str) -> str | None:
    """Return 'exact' or 'subdomain' or None."""
    if not host or not candidate:
        return None
    cand = candidate.lower().lstrip(".")
    if host == cand:
        return "exact"
    if host.endswith("." + cand):
        return "subdomain"
    return None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch(url: str) -> tuple[int, str]:
    try:
        r = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=FETCH_TIMEOUT, allow_redirects=True
        )
        return r.status_code, r.text
    except requests.RequestException as e:
        return 0, f"<fetch error: {e}>"


def serpapi_search(query: str, api_key: str, engine: str = "google", num: int = 20) -> list[dict]:
    params = {"q": query, "api_key": api_key, "engine": engine, "num": num}
    try:
        r = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        return [{"error": str(e), "query": query}]
    out: list[dict] = []
    for item in data.get("organic_results", []) or []:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "source": item.get("source"),
                "domain": item.get("displayed_link"),
            }
        )
    for item in data.get("shopping_results", []) or []:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("source"),
                "source": "shopping",
                "price": item.get("price"),
            }
        )
    return out


# ---------- Profile loading ----------


def load_brand_context(brand_slug: str, profile_dir: Path) -> dict[str, Any]:
    profile_path = profile_dir / f"{brand_slug}_profile.json"
    if not profile_path.exists():
        sys.exit(f"profile not found: {profile_path}")
    profile = load_json(profile_path)

    whitelist_path = profile_dir / f"{brand_slug}_whitelist.json"
    whitelist = load_json(whitelist_path) if whitelist_path.exists() else None

    # Build authorized-domain set + reseller domains + amazon merchant ID + image URLs
    auth_domains_strong: set[str] = set()
    auth_domains_claimed: set[str] = set()
    amazon_merchant_ids: set[str] = set()

    # From profile
    for d in profile.get("brand", {}).get("all_official_domains", []) or []:
        auth_domains_strong.add(d.lower().lstrip("www."))
    ap = profile.get("authorized_presence", {}) or {}
    for r in ap.get("authorized_resellers_high_confidence", []) or []:
        h = hostname(r.get("url", ""))
        if h:
            auth_domains_strong.add(h.lstrip("www."))
    for r in ap.get("authorized_resellers_to_verify", []) or []:
        h = hostname(r.get("url", ""))
        if h:
            auth_domains_claimed.add(h.lstrip("www."))
    for m in ap.get("marketplace_storefronts", []) or []:
        if m.get("platform", "").lower() == "amazon" and m.get("merchant_id"):
            amazon_merchant_ids.add(m["merchant_id"])

    # From whitelist (Sherlock Holmes case)
    if whitelist:
        for party in whitelist.get("authorized_parties", []) or []:
            for d in party.get("official_domains", []) or []:
                auth_domains_strong.add(d.lower().lstrip("www."))

    # Image URLs (from raw_artifacts/products_full.json — same dir structure)
    image_urls: set[str] = set()
    raw_path = (
        profile_dir.parent
        / "memory"
        / "BRAND_PROFILES"
        / brand_slug
        / "raw_artifacts"
        / "products_full.json"
    )
    if raw_path.exists():
        try:
            raw = load_json(raw_path)
            for p in raw.get("products", []) or []:
                for img in p.get("images", []) or []:
                    src = img.get("src", "")
                    if src:
                        image_urls.add(src.split("?")[0])
        except Exception:
            pass

    # Optional pre-built phash index (built by image_hash_index.py)
    image_index = None
    if _IH_AVAILABLE:
        idx_path = (
            profile_dir.parent
            / "memory"
            / "BRAND_PROFILES"
            / brand_slug
            / "image_index.json"
        )
        if idx_path.exists():
            try:
                image_index = load_json(idx_path)
            except Exception:
                image_index = None

    return {
        "slug": brand_slug,
        "profile": profile,
        "whitelist": whitelist,
        "auth_domains_strong": auth_domains_strong,
        "auth_domains_claimed": auth_domains_claimed,
        "amazon_merchant_ids": amazon_merchant_ids,
        "image_urls": image_urls,
        "image_index": image_index,
        "distinctive_phrases": DISTINCTIVE_PHRASES_BY_BRAND.get(brand_slug, []),
        "sku_patterns": SKU_PREFIX_BY_BRAND.get(brand_slug, []),
        "price_floor": PRICE_FLOOR_USD.get(brand_slug),
        "brand_name": profile.get("brand", {}).get("name", brand_slug),
    }


# ---------- Scoring ----------


def score_seller(
    url: str,
    html: str,
    status: int,
    ctx: dict[str, Any],
    seed_title: str | None = None,
    seed_snippet: str | None = None,
) -> dict[str, Any]:
    """Score a single seller listing. Pure function; returns verdict dict.

    `seed_title` and `seed_snippet` come from the SerpAPI result and are used as
    a content fallback when the actual page fetch is blocked (403) or returns a
    JS-rendered stub. Concatenated to the page text before regex/string scoring.
    """
    seed_blob = " ".join(filter(None, [seed_title, seed_snippet]))
    # If the HTML is small (likely a stub or blocked), the SerpAPI snippet/title
    # carries most of the content signal. Always concatenate it.
    text = ((html or "") + " " + seed_blob).lower()
    host = hostname(url)
    fetch_yielded_content = bool(html and len(html) > 2000)
    score = 0
    reasons: list[str] = []
    evidence: list[str] = []

    # 1. Whitelist domain match
    domain_hit_kind = None
    for d in ctx["auth_domains_strong"]:
        kind = host_matches(host, d)
        if kind:
            domain_hit_kind = kind
            score += WEIGHTS[
                "whitelist_domain_exact" if kind == "exact" else "whitelist_domain_subdomain"
            ]
            reasons.append(f"domain {host} {kind}-matches authorized domain {d}")
            evidence.append(f"matched_domain={d}")
            break
    claimed_reseller_hit = False
    if not domain_hit_kind:
        for d in ctx["auth_domains_claimed"]:
            kind = host_matches(host, d)
            if kind:
                score += WEIGHTS["authorized_reseller_claimed"]
                reasons.append(
                    f"domain {host} matches claimed-but-unverified reseller {d}"
                )
                evidence.append(f"claimed_reseller={d}")
                claimed_reseller_hit = True
                break

    # 2. Amazon merchant ID match
    amazon_merchant_hit = False
    if "amazon." in host:
        for mid in ctx["amazon_merchant_ids"]:
            if mid.lower() in text or mid in url:
                score += WEIGHTS["amazon_merchant_id_match"]
                reasons.append(f"Amazon merchant ID {mid} matches brand storefront")
                evidence.append(f"amazon_merchant={mid}")
                amazon_merchant_hit = True
                break

    # If this is a whitelisted seller (own domain or own Amazon storefront), the negative
    # signals below are expected — they're how we recognize the brand's own content.
    # Skip the negative block; verdict is authorized.
    is_whitelisted = bool(domain_hit_kind) or amazon_merchant_hit
    if is_whitelisted:
        verdict = "authorized"
        return {
            "seller_host": host,
            "url": url,
            "verdict": verdict,
            "score": score,
            "reasons": reasons,
            "evidence": evidence,
            "fetch_status": status,
        }

    # 3. Image URL exact match (lazy hotlink case)
    matched_imgs = [iu for iu in ctx["image_urls"] if iu.lower() in text]
    if matched_imgs:
        score += WEIGHTS["image_url_exact_match"]
        reasons.append(f"page hot-links {len(matched_imgs)} image URL(s) from brand CDN")
        evidence.extend(f"image_hotlink={u}" for u in matched_imgs[:3])

    # 3b. Perceptual image hash match — catches counterfeits that rehost brand photos.
    if ctx.get("image_index") and html:
        page_imgs = list({m.group(1) for m in PAGE_IMAGE_URL_RE.finditer(html)})[
            :MAX_IMAGES_TO_HASH_PER_PAGE
        ]
        best = None  # (dist, brand_entry, candidate_url)
        for cand_url in page_imgs:
            img = _IH.fetch_image(cand_url)
            if not img:
                continue
            cph, cdh = _IH.hash_image(img)
            matches = _IH.find_matches(
                cph, cdh, ctx["image_index"], threshold=_IH.MATCH_THRESHOLDS["weak"]
            )
            if matches and (best is None or matches[0]["min_dist"] < best[0]):
                best = (matches[0]["min_dist"], matches[0], cand_url)
        if best:
            dist, entry, cand_url = best
            if dist <= _IH.MATCH_THRESHOLDS["strong"]:
                score += WEIGHTS["image_phash_strong"]
                tier = "strong"
            else:
                score += WEIGHTS["image_phash_weak"]
                tier = "weak"
            reasons.append(
                f"image phash {tier}-match (dist={dist}) to brand image '{entry.get('product_title')}'"
            )
            evidence.append(f"phash_match_dist={dist}; brand_src={entry.get('src')}")
            evidence.append(f"candidate_image={cand_url}")

    # 4. Distinctive phrase match
    phrase_hits = [p for p in ctx["distinctive_phrases"] if p in text]
    if phrase_hits:
        weight = WEIGHTS["distinctive_phrase"] * len(phrase_hits)
        # tagline misuse if "most imitated, never duplicated" specifically
        for p in phrase_hits:
            if "most imitated" in p:
                weight += WEIGHTS["tagline_misuse"]
        score += weight
        reasons.append(f"matched {len(phrase_hits)} distinctive brand phrase(s)")
        evidence.extend(f"phrase={p}" for p in phrase_hits)

    # 5. SKU prefix match
    sku_hits: list[str] = []
    for pat in ctx["sku_patterns"]:
        m = re.search(pat, html or "", re.IGNORECASE)
        if m:
            sku_hits.append(m.group(0))
    if sku_hits:
        score += WEIGHTS["sku_prefix_present"]
        reasons.append(f"page contains brand SKU pattern(s): {', '.join(sku_hits[:5])}")
        evidence.extend(f"sku={s}" for s in sku_hits[:5])

    # 6. Price-floor violation
    if ctx.get("price_floor"):
        prices = [
            float(m.group(1))
            for m in re.finditer(r"\$([0-9]{1,4}(?:\.[0-9]{2})?)", html or "")
        ]
        below = [p for p in prices if 0.5 < p < ctx["price_floor"]]
        if below:
            # only fire if brand name is also present (avoid noise on unrelated pages)
            if ctx["brand_name"].lower() in text:
                score += WEIGHTS["price_below_floor"]
                reasons.append(
                    f"prices below brand floor ${ctx['price_floor']}: ${min(below):.2f}"
                )
                evidence.append(f"price_floor_violation_min=${min(below):.2f}")

    # 7. Patented-claim language (downweight if no whitelist hit — likely overreach)
    pat_hits = [p for p in PATENTED_CLAIM_PATTERNS if re.search(p, text)]
    if pat_hits and not domain_hit_kind:
        score += WEIGHTS["patented_claim_language"]
        reasons.append(
            f"page uses authority-claim language without whitelist match: {', '.join(pat_hits[:3])}"
        )
        evidence.extend(f"claim_language={p}" for p in pat_hits[:3])

    # 8. Brand name in title — small downweight only if no other authorized signal
    if ctx["brand_name"].lower() in text and not domain_hit_kind:
        # neutral by itself; small nudge toward unauthorized so the verdict thresholds work
        score += WEIGHTS["brand_name_in_title"]
        reasons.append(
            f"brand name '{ctx['brand_name']}' present on a non-whitelisted seller"
        )

    # If we used the SerpAPI seed text (because the page was blocked/stub),
    # note that in evidence so the user understands the basis.
    if seed_blob and not fetch_yielded_content:
        evidence.append(f"content_source=serpapi_seed (page fetch returned status={status})")

    # Verdict
    if status == 0 or status >= 500:
        verdict = "review"
        reasons.append(f"fetch failed (status {status}); manual review required")
    elif score >= 50:
        verdict = "authorized"
    elif score <= -40:
        verdict = "unauthorized"
    else:
        verdict = "review"

    return {
        "seller_host": host,
        "url": url,
        "verdict": verdict,
        "score": score,
        "reasons": reasons,
        "evidence": evidence,
        "fetch_status": status,
    }


# ---------- Discovery ----------


def discover_candidates(ctx: dict[str, Any], api_key: str, max_results: int) -> list[dict]:
    brand = ctx["brand_name"]
    queries: list[str] = []

    if ctx["slug"] == "handson-gloves":
        queries = [
            f'"HandsOn Gloves" -site:handsongloves.com',
            f'"HandsOn Pet Grooming Gloves" site:amazon.com',
            f'"HandsOn Animal Gloves" site:ebay.com',
            f'"handson grooming glove" site:aliexpress.com',
            f'"HandsOn" pet grooming glove site:walmart.com',
            f'"HandsOn" grooming glove site:etsy.com',
        ]
    elif ctx["slug"] == "sherlock-holmes":
        queries = [
            f'"Just Deduce It" sherlock holmes -site:sherlockholmes.com',
            f'"Sherlock Holmes Gazette" digital download',
            f'"sherlock holmes company" merchandise -site:sherlockholmes.com',
            f'"sherlock holmes" hoodie t-shirt -site:lego.com -site:conandoyleestate.com',
        ]

    seen: dict[str, dict] = {}
    for q in queries:
        results = serpapi_search(q, api_key, num=10)
        for r in results:
            u = r.get("url")
            if not u or "error" in r:
                continue
            if u in seen:
                continue
            seen[u] = r
            if len(seen) >= max_results:
                break
        if len(seen) >= max_results:
            break
        time.sleep(0.4)  # be nice to SerpAPI rate limits

    return list(seen.values())[:max_results]


# ---------- Main ----------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--brand", required=True, help="brand slug (e.g. handson-gloves)")
    ap.add_argument("--url", action="append", default=[], help="seller URL (repeatable)")
    ap.add_argument("--discover", action="store_true", help="run SerpAPI discovery")
    ap.add_argument("--max", type=int, default=15, help="max discovered candidates")
    ap.add_argument("--output", default="-", help="output JSON path or '-' for stdout")
    ap.add_argument(
        "--profile-dir",
        default=str(Path(__file__).parent / "output"),
        help="directory containing <brand>_profile.json",
    )
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir).resolve()
    ctx = load_brand_context(args.brand, profile_dir)

    candidates: list[dict] = [{"url": u, "title": None, "source": "user"} for u in args.url]

    if args.discover:
        api_key = os.environ.get("SERPAPI_KEY", "").strip()
        if not api_key:
            sys.exit("SERPAPI_KEY not set; export it or omit --discover")
        discovered = discover_candidates(ctx, api_key, args.max)
        candidates.extend(discovered)

    if not candidates:
        sys.exit("no candidates — pass --url and/or --discover")

    verdicts = []
    for cand in candidates:
        url = cand.get("url")
        if not url:
            continue
        status, html = fetch(url)
        v = score_seller(
            url,
            html,
            status,
            ctx,
            seed_title=cand.get("title"),
            seed_snippet=cand.get("snippet"),
        )
        v["seed_title"] = cand.get("title")
        v["seed_source"] = cand.get("source")
        verdicts.append(v)

    summary = {
        "brand": args.brand,
        "candidates_checked": len(verdicts),
        "verdict_counts": {
            "authorized": sum(1 for v in verdicts if v["verdict"] == "authorized"),
            "unauthorized": sum(1 for v in verdicts if v["verdict"] == "unauthorized"),
            "review": sum(1 for v in verdicts if v["verdict"] == "review"),
        },
        "verdicts": verdicts,
    }
    text = json.dumps(summary, indent=2)
    if args.output == "-":
        print(text)
    else:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output} ({len(verdicts)} verdicts)")


if __name__ == "__main__":
    main()
