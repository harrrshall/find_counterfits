# find_counterfits

A two-stage system for **brand-counterfeit detection**:

1. A **Brand Discovery Agent** (driven by `AGENT.md`) that takes a brand name and produces a verified, schema-valid brand profile — domain footprint, products, IP, authorized presence, fake patterns.
2. A **classifier** that takes those profiles and a list (or SerpAPI-discovered list) of seller URLs and returns `authorized` / `unauthorized` / `review` verdicts with reasons and evidence.

Bundled with a perceptual-image-hash index, a CLI report renderer, and a Streamlit testing UI.

The repo currently ships seed data for two brands:

| Brand | Profile | Notes |
|---|---|---|
| **HandsOn Gloves** | [`output/handson-gloves_profile.json`](output/handson-gloves_profile.json) | Texas family-owned company; patented (USD858906, USD893111); active counterfeit litigation. Strong IP, narrow product. |
| **Sherlock Holmes** | [`output/sherlock-holmes_profile.json`](output/sherlock-holmes_profile.json) + [`whitelist`](output/sherlock-holmes_whitelist.json) | UK Ltd #06039145; not a Conan Doyle Estate licensee. Public-domain character — whitelist drives the rule. |

---

## High-level architecture

```
                  ┌──────────────────────────────────────────────────────┐
                  │                                                      │
                  │   Brand name (user input)                            │
                  │                │                                     │
                  │                ▼                                     │
                  │   ┌───────────────────────────────┐                  │
                  │   │  Brand Discovery Agent        │                  │
                  │   │  (driven by AGENT.md)         │                  │
                  │   │  - Phase 1: identity          │                  │
                  │   │  - Gate 1                     │                  │
                  │   │  - Phase 2: deep profile      │                  │
                  │   │  - Gate 2                     │                  │
                  │   │  - Phase 3: write outputs     │                  │
                  │   └────────────────┬──────────────┘                  │
                  │                    │                                 │
                  │                    ▼                                 │
                  │     output/<brand>_profile.{json,md}                 │
                  │     output/<brand>_whitelist.json   (optional)       │
                  │     memory/BRAND_PROFILES/<brand>/...                │
                  │            └ raw_artifacts/products_full.json        │
                  │            └ image_index.json   (built next)         │
                  │                                                      │
                  │  ───────────  STAGE 1 — DISCOVERY/SEEDING  ───────── │
                  └──────────────────────────────────────────────────────┘
                                       │
                                       │  consumed by
                                       ▼
                  ┌──────────────────────────────────────────────────────┐
                  │                                                      │
                  │   ┌───────────────────────────────┐                  │
                  │   │  image_hash_index.py          │                  │
                  │   │   - downloads each brand img  │                  │
                  │   │   - phash + dhash (8x8 = 64b) │                  │
                  │   │   - persists to image_index.  │                  │
                  │   │     json under memory/...     │                  │
                  │   └────────────────┬──────────────┘                  │
                  │                    │                                 │
                  │   ┌────────────────▼──────────────┐                  │
                  │   │  classify.py                  │                  │
                  │   │   - load profile + whitelist  │                  │
                  │   │   - SerpAPI Google discovery  │                  │
                  │   │     OR user-supplied URLs     │                  │
                  │   │   - per candidate:            │                  │
                  │   │       fetch HTML              │                  │
                  │   │       SerpAPI snippet fallback│                  │
                  │   │       run signal block:       │                  │
                  │   │         - whitelist domain    │                  │
                  │   │         - amazon merchant id  │                  │
                  │   │         - image hotlink       │                  │
                  │   │         - pHash phash match   │                  │
                  │   │         - distinctive phrase  │                  │
                  │   │         - SKU prefix          │                  │
                  │   │         - price-floor break   │                  │
                  │   │         - authority claim     │                  │
                  │   │   - threshold → verdict       │                  │
                  │   └────────────────┬──────────────┘                  │
                  │                    │                                 │
                  │                    ▼                                 │
                  │   verdicts JSON  ← machine-readable                  │
                  │            │                                         │
                  │            ├─►  report.py     (rich CLI)             │
                  │            └─►  app.py        (Streamlit UI)         │
                  │                                                      │
                  │  ───────────  STAGE 2 — CLASSIFICATION  ──────────── │
                  └──────────────────────────────────────────────────────┘
```

Two stages, cleanly separated. Stage 1 is human-gated (the agent stops at Gate 1 and Gate 2 before writing files). Stage 2 is fully automatic and reads only the artifacts Stage 1 produced.

---

## How a verdict is computed

For each candidate seller URL the classifier:

1. **Fetches the HTML** with `requests` + a normal User-Agent. If the seller blocks (403) or returns a JS-stub (Amazon, Walmart, Etsy, Redbubble, eBay), the **SerpAPI title + snippet** that surfaced the URL is concatenated to whatever HTML was returned, so signal detection still has something to work with.
2. **Runs the signal block** — every signal carries a positive (authorized) or negative (unauthorized) weight. Weights are in `WEIGHTS` at the top of `classify.py`, current values:

   | Signal | Weight |
   |---|---:|
   | Whitelist domain exact match | **+90** |
   | Whitelist domain subdomain match | **+70** |
   | Amazon merchant-ID match against brand storefront | **+85** |
   | High-confidence authorized reseller | +60 |
   | Claimed-but-unverified reseller | +30 |
   | Image phash strong match (Hamming ≤ 6 / 64) | **−85** |
   | Image phash weak match (Hamming ≤ 10 / 64) | −45 |
   | Image URL hot-linked from brand CDN | −75 |
   | Distinctive brand phrase (per phrase) | −35 |
   | Tagline misuse ("Most Imitated, Never Duplicated") | −50 (additive) |
   | Brand SKU prefix in HTML | −40 |
   | Price below brand floor | −25 |
   | Authority-claim language on non-whitelisted seller | −20 |
   | Brand name on a non-whitelisted seller | −15 |

3. **Whitelist short-circuits.** If the seller is on a whitelisted domain or matches the brand's Amazon merchant ID, the verdict is `authorized` and negative signals are skipped (those are *expected* on the brand's own pages).
4. **Verdict thresholds:** `score ≥ 50 → authorized`, `score ≤ −40 → unauthorized`, otherwise `review`.

Every verdict carries `reasons` (human-readable) and `evidence` (machine-readable artifacts that backed each reason).

---

## Repo layout

```
find_counterfits/
├── AGENT.md                    Brand Discovery Agent spec (drives stage 1)
├── README.md                   this file
├── CLASSIFIER.md               classifier deep-dive docs
│
├── classify.py                 stage-2 core: discovery + scoring
├── image_hash_index.py         pHash index builder + matcher
├── report.py                   rich CLI verdict renderer
├── app.py                      Streamlit testing UI
│
├── .env                        SERPAPI_KEY (chmod 600, gitignored)
│
├── output/                     final deliverables
│   ├── handson-gloves_profile.{json,md}
│   ├── sherlock-holmes_profile.{json,md}
│   ├── sherlock-holmes_whitelist.json
│   └── sample_verdicts_*.json  test runs
│
└── memory/                     agent memory (persists across sessions)
    ├── INDEX.md                profiled-brand index
    ├── LEARNINGS.md            patterns to keep applying
    ├── MISTAKES.md             patterns to stop repeating
    └── BRAND_PROFILES/<slug>/
        ├── profile_v1.{json,md}
        ├── session_log_*.md
        ├── image_index.json
        └── raw_artifacts/
            ├── products_full.json
            └── homepage.html
```

---

## Getting started

```bash
# 1. Create venv + install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Drop your SerpAPI key into .env
echo 'SERPAPI_KEY=your_key_here' > .env
chmod 600 .env

# 3. Build the perceptual-hash index for each brand (one-time)
python image_hash_index.py build --brand handson-gloves
python image_hash_index.py build --brand sherlock-holmes
```

### Run the classifier (CLI)

```bash
# discover candidates via SerpAPI and classify them
python classify.py --brand handson-gloves --discover --max 10

# classify specific URLs
python classify.py --brand handson-gloves \
  --url https://www.amazon.com/dp/B0942X1K99 \
  --url https://example.com/some-listing
```

### Run the rich CLI report

```bash
python report.py --brand handson-gloves --discover --max 10
python report.py --brand sherlock-holmes --discover --max 10
python report.py --brand handson-gloves --from-file output/sample_verdicts_handson_v2.json
```

### Run the Streamlit UI

```bash
streamlit run app.py
# opens at http://localhost:8501
```

The UI has:
- Brand radio (HandsOn Gloves / Sherlock Holmes — the seed profiles)
- SerpAPI discovery toggle + max-candidates slider
- "Paste your own URLs" textarea
- Result table + expandable per-candidate cards (reasons, evidence, raw JSON)
- Download-as-JSON button

---

## Adding a new brand

The Brand Discovery Agent (`AGENT.md`) is what produces a new profile. The agent's workflow is human-gated:

1. Run the agent with the brand name.
2. **Gate 1 — Brand Identity**: agent produces a verified Brand Identity Card; you approve before the deep profile begins.
3. **Gate 2 — Deep Profile**: agent compiles the full schema; you approve before files are written.
4. Files land in `output/<slug>_profile.{json,md}` and `memory/BRAND_PROFILES/<slug>/`.
5. Build the perceptual-hash index: `python image_hash_index.py build --brand <slug>`.
6. The classifier auto-loads the new brand on the next run — add it to `BRAND_OPTIONS` in `app.py` if you want it in the Streamlit UI's radio.

See `AGENT.md` for the full schema, hard rules, and self-improvement protocol.

---

## Limitations

- **JS-rendered marketplace pages.** `requests` can't see what's behind a hydrate step. The SerpAPI snippet/title fallback covers most of this, but the highest-value upgrade is a headless-browser fetcher (Playwright / Chromium) that runs JS before scoring. Not built — kept the system SerpAPI-only.
- **Image-hash false positives on dropshipped POD goods.** When a category is dominated by print-on-demand (Sherlock Holmes T-shirts), the same factory output appears across many sellers. Image-hash flags them all; the cure is to bias the classifier toward textual signals (phrases, SKU prefixes) for those product types.
- **Trademark serial numbers** are flagged as `open_question` in both profiles. USPTO TSDR / Justia 403'd from the discovery environment. Run a direct registry lookup to fill in.
- **No persistence/diffing.** Every run is a fresh shot. For an ongoing monitor, wrap `classify.py` in a cron job that diffs against prior verdicts and emits new-unauthorized alerts.

---

## Stack

Python 3.10+. Everything is a single file you can read in one sitting. Dependencies kept tight: `requests`, `Pillow`, `ImageHash`, `streamlit`, `rich`. SerpAPI for Google discovery.
