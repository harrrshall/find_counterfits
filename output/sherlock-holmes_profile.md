# Brand Profile — Sherlock Holmes (The Sherlock Holmes Company)

**Generated:** 2026-05-04 · **Agent:** AGENT.md v1.0 · **Schema:** 1.0

---

## Brand identity

| Field | Value |
|---|---|
| Brand | Sherlock Holmes |
| Trading name | The Sherlock Holmes Company |
| Legal entity | **THE SHERLOCK HOLMES COMPANY (UK) LTD** (Companies House #06039145, Active, incorporated 2007-01-02) |
| Registered office | Suite 58 Hampstead House, 179 Finchley Road, London, NW3 6BT, UK |
| Officers | Justin Shulman (Director, b. 1976-02), Marcelle Simone Shulman (Secretary) |
| Primary domain | `sherlockholmes.com` (registered 1997-05-07; current Ltd took over) |
| Industry | E-commerce retail of themed merchandise (SIC 47789) |
| HQ | United Kingdom |
| Parent | Independent |

**One-liner:** London-registered online store selling Sherlock-Holmes-themed merchandise (apparel, accessories, POD goods, collectibles) via a Shopify storefront. **Not a licensee of the Conan Doyle Estate Ltd.**

---

## Critical context for downstream classifier

1. **Sherlock Holmes is a fictional character largely in the public domain** (US: pre-1928 stories; UK: ACD copyright expired 1980). Anyone may legally sell Sherlock-Holmes-themed merchandise.
2. **This brand is NOT the trademark holder.** The SHERLOCK HOLMES word mark is owned by **Conan Doyle Estate Limited** (USPTO #4313984, #4690745). The Estate's licensing page does not list this brand.
3. The "Official Site" tagline on `sherlockholmes.com` is **self-asserted**, not licensed.
4. Therefore: a "real vs counterfeit" classifier keyed on "Sherlock Holmes branded merch" will produce false positives. **Downstream classification must be limited to copying of THIS BRAND's specific assets** (product photography, distinctive phrases, logo, signature SKUs).

---

## Domain footprint

| Domain | Role |
|---|---|
| `sherlockholmes.com` | Primary apex (canonical) |
| `www.sherlockholmes.com` | 301 → apex |
| `sherlockholmes.shop` | Used for `sales@sherlockholmes.shop`; HTTP root redirects → `www.sherlockholmes.com/collections/all/` |

Platform: Shopify (`shop_id=83785974069`). CDN: `cdn.shopify.com`. Edge: Cloudflare.

---

## Visual identity

- **Primary logo (gold wordmark):** `https://sherlockholmes.com/cdn/shop/files/sherlock-holmes_gold-New.png?v=1697305115` (445×184)
- **Favicon:** `https://sherlockholmes.com/cdn/shop/files/FAVICON_2630f2a3-b726-4bdd-a8c3-be2a493f4e38.png`
- **Heading font:** `Sherlock-Script` (custom webfont)
- **Body palette:** white background, black text; gold accent (exact hex not exposed)

---

## Textual identity

- **Self-asserted slogan:** "Official Site" (not licensed)
- **Distinctive product phrase: "Just Deduce It"** — used across 12 SKUs (suitcase, sticker set, tumbler, mug, sweatshirt, hoodie, pillow, t-shirt, kids hoodie, water bottle, black-glossy mug). Trademark status: not confirmed registered.
- Distinctive long-form phrases:
  - "Step into the world of Sherlock Holmes and prepare to be captivated by the allure of mystery and intrigue!"
  - "Your One-Stop Shop for All Things Sherlock"
  - "From 221B to Your Doorstep"
- Naming convention: `Sherlock Holmes - {sub-line} - {product type}`

---

## Catalog summary

| Metric | Value |
|---|---|
| Total SKUs | **126** |
| "Bestsellers" count | 38 |
| Base currency | **GBP** (range £2.32 – £2,250) |
| Default presentment | INR (Shopify Markets multiplier ~140–180×) |
| Free shipping | over £50 |
| Vendors (raw field) | "Sherlock Holmes" 57 · "The Sherlock Holmes Company" 40 · "Printify" 12 · "sherlock holmes" 17 |

**Full catalog (all 126 products with images, variants, tags) saved at:** `./memory/BRAND_PROFILES/sherlock-holmes/raw_artifacts/products_full.json`

---

## Authorized presence

| Platform | Handle | Verified? |
|---|---|---|
| Instagram | `@thesherlockholmescompany` | ❓ unverified |
| Facebook | `SherlockHolmesCompany` | ❓ unverified |
| TikTok | `@sherlock.holmes.uk` | ❓ unverified |
| LinkedIn | `the-sherlock-holmes-memorabilia-company` | ❓ unverified — name mismatch (refers to a related Ltd #02666173 at same address) |

- **Authorized resellers:** none disclosed.
- **Marketplace storefronts:** none disclosed.

---

## Legal / IP

- **Trademarks owned by this entity:** none confirmed (open question — direct UKIPO/USPTO walk needed)
- **Third-party trademarks that affect this brand:** SHERLOCK HOLMES (Conan Doyle Estate Limited, USPTO #4313984 & #4690745)
- **Is this brand a Conan Doyle Estate licensee?** **No** — verified against the Estate's licensing page.
- **DMCA / IP contact published:** none. Best contact: `sales@sherlockholmes.shop`
- **Brand Registry enrollments:** none visible.
- **Companies House status:** Active, accounts current.

---

## Pricing baseline

- Base currency: **GBP**
- Lowest authorized price (last 90 days): **£2.32**
- Highest authorized price: **£2,250**
- Free shipping threshold: £50
- MAP policy: none published

Anything significantly below site prices (after currency normalization) on a third-party marketplace is a downstream red flag.

---

## Known fake patterns

The brand publishes no "spot the fake" guide. No public news of past counterfeit busts.

**Agent-inferred high-value signals for the downstream classifier:**

1. Image-hash match against any `images[].src` URL in `products_full.json`
2. Listing copy containing the exact phrase **"Just Deduce It"** + Sherlock visual motif
3. Use of the gold wordmark logo (`sherlock-holmes_gold-New.png`) outside this domain
4. Use of the `Sherlock-Script` custom webfont in seller listings
5. Replicas of `Sherlock Holmes Gazette - Issue NN - Digital Download` (uniquely identifying)
6. Any seller claiming "Official Sherlock Holmes Site" outside `sherlockholmes.com`

**Caveats:**
- 12 SKUs flagged as `vendor=Printify` are POD goods. Anyone can produce these on the same back-end. Image-hash match is the only reliable signal for these.
- The "Sherlock Holmes" name itself is NOT a usable signal — too many legitimate sellers exist.

---

## Open questions (carry into next revision)

1. UKIPO + USPTO direct walk for trademarks owned by Companies House #06039145
2. "Just Deduce It" trademark registration status
3. Verified-badge confirmation on IG/FB/TikTok/LinkedIn
4. Marketplace presence (Amazon Brand Store, Flipkart, Myntra, Etsy)
5. Relationship between #06039145 and #02666173 (Memorabilia Co.)
6. Exact gold/yellow accent hex
7. Historical DMCA / takedown filings by this entity

---

## Sources

- `https://sherlockholmes.com/` (live)
- `https://sherlockholmes.com/policies/terms-of-service`
- `https://sherlockholmes.com/policies/privacy-policy`
- `https://sherlockholmes.com/pages/about-us`
- `https://sherlockholmes.com/products.json`
- `https://find-and-update.company-information.service.gov.uk/company/06039145`
- `https://find-and-update.company-information.service.gov.uk/company/06039145/officers`
- `https://rdap.verisign.com/com/v1/domain/sherlockholmes.com`
- `https://conandoyleestate.com/licensing/trademarks-and-copyrights`
- `https://trademarks.justia.com/854/47/sherlock-85447511.html`
- `https://en.wikipedia.org/wiki/Klinger_v._Conan_Doyle_Estate,_Ltd.`
- `https://www.archive.sherlockian.net/acd/copyright.html`
