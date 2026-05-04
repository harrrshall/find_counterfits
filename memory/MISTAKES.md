# Mistakes Log

## [seed] Confusing brand with parent company
**Category:** wrong-brand
**What happened:** Profiled "Maggi" but listed Nestlé's domains, Nestlé's trademarks, and Nestlé's social handles.
**Root cause:** Conflated the parent corporation with the brand-line being researched.
**Prevention rule:** First action in Phase 1 is explicitly answer: "Is this a brand, a product line, or a parent company? What are the other two?"
**Verification step to add:** Brand Identity Card must list both the brand and its parent (if any) on separate lines.

## [seed] Trusting a high-ranking fake official site
**Category:** unverified-claim
**What happened:** Took the top Google result as the official domain. It was a counterfeit storefront with high SEO.
**Root cause:** Treated search ranking as authority signal.
**Prevention rule:** Primary domain must be cross-checked against ≥3 of: Wikipedia, LinkedIn, Crunchbase, official social profile bio link, public registry filing, app store developer page.
**Verification step to add:** Run WHOIS — if domain age < 2 years for a brand claiming to be older, escalate.

## [seed] Missing regional rights holder
**Category:** missed-source
**What happened:** Profiled a global brand without realizing its India trademark is held by a different licensee.
**Root cause:** Assumed global brand = single rights holder worldwide.
**Prevention rule:** Always check the trademark registry of the brand's HQ country AND the user's primary market.
**Verification step to add:** In Phase 2.6, search ≥2 trademark registries.

## [seed] Treating a category descriptor as a trademark
**Category:** false-assumption
**What happened:** Listed "pure honey" as a distinctive phrase. It is generic.
**Root cause:** Did not check trademark register before flagging a phrase.
**Prevention rule:** Distinctive phrases must be ≥8 words AND not appear in the top 1M Google results as a generic phrase.
**Verification step to add:** Test each candidate phrase as an exact-match Google query — if >100k results, it's not distinctive.

## [seed] Outdated logo
**Category:** outdated-info
**What happened:** Captured a logo that was retired 3 years ago, still indexed in Google Images.
**Root cause:** Used Google Images instead of the brand's current homepage.
**Prevention rule:** Logos are sourced ONLY from the brand's current homepage / press kit / brand guidelines page.

## [seed] Gate violation (silent approval)
**Category:** gate-violation
**What happened:** User said "ok cool" after Phase 1 and I treated it as Gate 1 approval, then they corrected me later.
**Root cause:** Ambiguous user response treated as "yes."
**Prevention rule:** "Yes," "approve," "proceed," "go ahead," "looks correct" = approval. Anything else (including emojis, "ok," "cool," "sure") → ask again explicitly.
