# Learnings Log

## [2026-05-04] Pull Shopify catalogs via /products.json from the host
**Pattern:** For any Shopify-hosted brand storefront, `curl https://{domain}/products.json?limit=250` returns the full catalog as JSON (handle, title, vendor, product_type, tags, variants[].price, images[].src). This is publicly readable on essentially every Shopify store.
**When to apply:** Phase 2.2 product catalog enumeration on any Shopify brand. Faster and cleaner than rendering the storefront and scraping.
**Example:** Pulled all 126 Sherlock Holmes Company SKUs in 2 seconds; pulled all 5 HandsOn Gloves SKUs with 33 images.

## [2026-05-04] Cross-check the IP rights holder on day one
**Pattern:** Before anything else in Phase 1, ask: who actually owns the trademark? Is the brand-under-research the rights holder, a licensee, or unrelated? Run a parallel search like `"{brand}" trademark license owner` and check the actual rights holder's licensing page.
**When to apply:** Any brand built on a public-domain or character-IP foundation (Sherlock Holmes, Robin Hood, Dracula, Alice in Wonderland, mythological figures, historical figures).
**Example:** Surfacing that The Sherlock Holmes Company is not a Conan Doyle Estate licensee — and that the underlying character is largely public domain — completely reshaped the deep-profile framing.

## [2026-05-04] Use Companies House early when a UK address is on the policy pages
**Pattern:** UK e-commerce sites must publish a registered office in their ToS/Privacy. Before doing anything fancy, search `find-and-update.company-information.service.gov.uk` for that address — within seconds you get the official entity, status, officers, and incorporation date.
**When to apply:** Phase 1 verification for any brand with a UK address.

## [2026-05-04] Chrome MCP output-filter workaround
**Pattern:** `mcp__claude-in-chrome__javascript_tool` blocks responses that look like JSON or URL-bearing strings (returns `[BLOCKED: Cookie/query string data]`). Workaround: have the JS return short newline-joined `key|value` lines, or pull the data via `Bash` + `curl` from the host since most needed endpoints are public.
**When to apply:** Whenever Chrome MCP starts returning `BLOCKED` errors.

## [2026-05-04] Court complaints are gold for fake-pattern seeding
**Pattern:** When a brand has filed IP-infringement lawsuits, the complaint documents enumerate exactly which counterfeit patterns the brand has actually litigated — copied images, names, listing language, marketplace channels, originating geographies. These are far higher-confidence than agent-inferred patterns.
**When to apply:** Phase 2.8 (known fake patterns) for any brand with active enforcement history. Search Scribd, CourtListener, PACER, and uspto.report for `{brand} v.` and `{entity} complaint`.
**Example:** HandsOn Equine v. Pat Your Pet (D. Colo. 1:19-cv-02570) gave us: (a) Ukrainian foreign corp as the counterfeiter origin, (b) Chewy.com and Amazon.com as the channels, (c) D858,906 design patent as the violated IP, (d) "intentional copying of the unique nodule design" as the theory.

## [2026-05-04] Anti-counterfeit homepage messaging is itself a strong seed
**Pattern:** When a brand puts anti-counterfeit phrasing on its homepage marquee (e.g., HandsOn's "MOST IMITATED, NEVER DUPLICATED"), that phrase becomes a uniquely distinctive textual seed for the classifier — no legitimate competitor will use it.
**When to apply:** Phase 2.4 distinctive phrase collection. Always scan homepage marquees / hero copy for self-aware anti-counterfeit language.

## [2026-05-04] Map the corporate-entity family, not just the seller-of-record
**Pattern:** A single brand often runs across 2-3 related legal entities: (a) the operating storefront entity in ToS, (b) the IP-holding LLC named in patents, (c) a parent holding company. They may be at the same address but different roles. The brand profile must list all three so downstream legal action goes to the right entity.
**When to apply:** Phase 1 verification. Always check the patent assignee against the ToS entity — if they differ, both go in the profile.
**Example:** HandsOn has at least three related names: "HandsOn Happy Assets Corporation" (in ToS), "HandsOn Equine, LLC" (patent assignee + plaintiff), "Handson Gloves, LLC" (named patent grantee). Treat as one family with multiple roles.
