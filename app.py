"""
Counterfeit-detection tester — a one-page Streamlit UI.

Run:
    source .venv/bin/activate
    streamlit run app.py

The UI lets you:
- Pick a brand (HandsOn Gloves or Sherlock Holmes — default options)
- Choose mode: SerpAPI discovery, paste-your-own URLs, or both
- Run the classifier and see verdicts as a colored table + expandable cards
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the existing classifier — its _load_dotenv() runs on import,
# which means SERPAPI_KEY from .env is already populated.
import classify  # noqa: E402

BRAND_OPTIONS = {
    "HandsOn Gloves":   "handson-gloves",
    "Sherlock Holmes":  "sherlock-holmes",
}

VERDICT_COLOR = {
    "authorized":   "#16a34a",
    "unauthorized": "#dc2626",
    "review":       "#ca8a04",
}
VERDICT_LABEL = {
    "authorized":   "✓ AUTHORIZED",
    "unauthorized": "✗ UNAUTHORIZED",
    "review":       "? REVIEW",
}

st.set_page_config(
    page_title="Counterfeit Tester",
    page_icon="🔍",
    layout="wide",
)

# ---------- Sidebar ----------

with st.sidebar:
    st.title("🔍 Counterfeit Tester")
    st.caption("Pick a brand. Hit Run. See the verdicts.")

    brand_label = st.radio(
        "Brand",
        list(BRAND_OPTIONS.keys()),
        index=0,
        help="Pre-loaded brand profiles. Add more by writing new "
        "`output/<slug>_profile.json` files.",
    )
    brand_slug = BRAND_OPTIONS[brand_label]

    st.divider()
    st.subheader("Discovery")
    use_discover = st.checkbox("Discover via SerpAPI", value=True)
    max_results = st.slider("Max candidates", 1, 30, 8, disabled=not use_discover)

    st.subheader("Or paste URLs")
    urls_raw = st.text_area(
        "One URL per line",
        height=120,
        placeholder="https://example.com/listing\nhttps://example.com/another",
    )

    serp_present = bool(os.environ.get("SERPAPI_KEY"))
    st.divider()
    if serp_present:
        st.success("SERPAPI_KEY loaded from .env")
    else:
        st.warning("No SERPAPI_KEY in env — discovery disabled")

    run = st.button("Run classifier", type="primary", use_container_width=True)

# ---------- Body ----------

st.title(f"{brand_label}")

# Show brand info card
profile_path = PROJECT_ROOT / "output" / f"{brand_slug}_profile.json"
if profile_path.exists():
    with st.expander("Brand profile (data the classifier uses)", expanded=False):
        prof = json.loads(profile_path.read_text())
        b = prof.get("brand", {})
        cols = st.columns(3)
        cols[0].metric("Domain", b.get("primary_domain", "—"))
        cols[1].metric(
            "Total SKUs",
            (prof.get("products", {}).get("_summary", {}) or {}).get("total_skus", "—"),
        )
        cols[2].metric("HQ", b.get("hq_country", "—"))
        st.caption(b.get("one_liner", ""))
        st.json(b, expanded=False)


def run_classification() -> dict:
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
    if not urls and not use_discover:
        st.error("Pass URLs or enable Discovery.")
        st.stop()

    profile_dir = PROJECT_ROOT / "output"
    ctx = classify.load_brand_context(brand_slug, profile_dir)

    candidates: list[dict] = [
        {"url": u, "title": None, "snippet": None, "source": "user"} for u in urls
    ]
    if use_discover:
        api_key = os.environ.get("SERPAPI_KEY", "").strip()
        if not api_key:
            st.error("SERPAPI_KEY not set; can't discover.")
            st.stop()
        with st.spinner("Querying SerpAPI..."):
            candidates.extend(classify.discover_candidates(ctx, api_key, max_results))

    if not candidates:
        st.error("No candidates found.")
        st.stop()

    verdicts: list[dict] = []
    progress = st.progress(0.0, text="Fetching & scoring candidates...")
    for i, cand in enumerate(candidates, 1):
        progress.progress(i / len(candidates), text=f"{i}/{len(candidates)} {cand.get('url','')}")
        url = cand.get("url")
        if not url:
            continue
        status, html = classify.fetch(url)
        v = classify.score_seller(
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
    progress.empty()

    return {
        "brand": brand_slug,
        "candidates_checked": len(verdicts),
        "verdict_counts": {
            "authorized":   sum(1 for v in verdicts if v["verdict"] == "authorized"),
            "unauthorized": sum(1 for v in verdicts if v["verdict"] == "unauthorized"),
            "review":       sum(1 for v in verdicts if v["verdict"] == "review"),
        },
        "verdicts": verdicts,
    }


def render_results(data: dict) -> None:
    counts = data["verdict_counts"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", data["candidates_checked"])
    c2.metric("✓ Authorized",   counts["authorized"])
    c3.metric("✗ Unauthorized", counts["unauthorized"])
    c4.metric("? Review",       counts["review"])

    st.divider()
    st.subheader("Summary table")
    rows = [
        {
            "#":         i + 1,
            "Verdict":   VERDICT_LABEL.get(v["verdict"], v["verdict"]),
            "Score":     v["score"],
            "Seller":    v.get("seller_host") or "",
            "URL":       v.get("url", ""),
            "Reasons":   "; ".join(v.get("reasons", [])) or "—",
            "HTTP":      v.get("fetch_status"),
        }
        for i, v in enumerate(data["verdicts"])
    ]
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL", width="medium"),
            "Score": st.column_config.NumberColumn(format="%+d"),
        },
    )

    st.divider()
    st.subheader("Per-candidate details")
    for i, v in enumerate(data["verdicts"], 1):
        color = VERDICT_COLOR.get(v["verdict"], "#666")
        label = VERDICT_LABEL.get(v["verdict"], v["verdict"])
        with st.expander(
            f"#{i}  {label}   score {v['score']:+d}   ·   {v.get('seller_host','')}",
            expanded=v["verdict"] == "unauthorized",
        ):
            st.markdown(
                f"<div style='border-left: 4px solid {color}; padding-left: 1rem;'>"
                f"<a href='{v.get('url','')}' target='_blank'>{v.get('url','')}</a>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if v.get("reasons"):
                st.markdown("**Reasons**")
                for r in v["reasons"]:
                    st.markdown(f"- {r}")
            if v.get("evidence"):
                st.markdown("**Evidence**")
                for e in v["evidence"]:
                    st.markdown(f"<code>{e}</code>", unsafe_allow_html=True)
            with st.popover("Raw verdict JSON", use_container_width=True):
                st.json(v)

    st.divider()
    st.download_button(
        "Download verdicts as JSON",
        json.dumps(data, indent=2),
        file_name=f"verdicts_{data['brand']}.json",
        mime="application/json",
        use_container_width=True,
    )


if run:
    data = run_classification()
    st.session_state["last_result"] = data

if "last_result" in st.session_state:
    render_results(st.session_state["last_result"])
else:
    st.info("👈 Configure on the left, then click **Run classifier**.")
    st.caption(
        "Defaults to **HandsOn Gloves** with SerpAPI discovery on. "
        "Switch the radio to **Sherlock Holmes** anytime — its profile + whitelist + 575-image "
        "perceptual-hash index are already loaded."
    )
