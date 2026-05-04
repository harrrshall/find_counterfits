# Session log — HandsOn Gloves

**Date:** 2026-05-04
**Agent version:** AGENT.md v1.0
**Time spent:** ~25 min

## What was asked
Profile HandsOn Gloves (handsongloves.com) as Brand B for the user's downstream "real vs counterfeit" classifier.

## What was done
- Phase 1: Verified entity via storefront ToS, RDAP WHOIS, and corroborated against patent records and court complaints. Identified the entity family (HandsOn Equine LLC / HandsOn Happy Assets Corp / HandsOn Gloves LLC).
- Gate 1: Approved (yes) by user.
- Phase 2: Pulled the full 5-SKU Shopify catalog. Extracted patent details (D858,906 + D893,111). Read both lawsuit complaints to extract the brand's documented counterfeit patterns.
- Gate 2: Approved (approve) by user.
- Phase 3: Wrote outputs to `output/` and mirrored to memory.

## What worked
- Reading the lawsuit complaints first paid off — it gave us the exact counterfeit patterns the brand has actually litigated against, which become high-confidence classifier signals.
- Cross-checking the patent assignee (HandsOn Equine LLC) against the storefront ToS entity (HandsOn Happy Assets Corporation) surfaced the multi-entity corporate family — important for downstream legal action attribution.
- The brand's "MOST IMITATED, NEVER DUPLICATED" tagline is itself a high-value distinctive seed.

## What didn't
- Justia trademark owner pages 403'd — couldn't directly enumerate HANDSON registration numbers.
- Could not directly query TX SOSDirect from this session — entity map remains partially unresolved.
- WebFetch on Instagram blocked by auth wall (same issue as Brand A).

## Time per phase (approx.)
- Phase 1: 8 min
- Phase 2: 13 min
- Phase 3: 4 min

## Decisions worth remembering
- For brands with active IP litigation, court filings are the single best source for authoritative counterfeit pattern lists. Always check Scribd / PACER / CourtListener early.
- A small SKU count (5 products) with a strong patent and active enforcement is a much better classifier seed than a large catalog of generic POD merch.
- "Most Imitated, Never Duplicated" pattern: brands that put anti-counterfeit messaging on the homepage are typically the right brands to seed a counterfeit pipeline with.
