#!/usr/bin/env python3
"""
Pretty CLI report for classifier verdicts.

Usage:
  python report.py --brand handson-gloves --discover --max 10
  python report.py --brand sherlock-holmes --from-file output/sample_verdicts.json
  python report.py --brand handson-gloves --url <url1> --url <url2>

Modes:
  --discover                run classify.py with SerpAPI discovery, then render
  --from-file <path>        render a previously-saved verdicts JSON
  --url <url> [--url ...]   classify specific URLs, then render

Reads SERPAPI_KEY from env when --discover is used.
"""

import argparse
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

VERDICT_STYLE = {
    "authorized":   ("✓ AUTHORIZED",  "bold green"),
    "unauthorized": ("✗ UNAUTHORIZED","bold red"),
    "review":       ("? REVIEW",      "bold yellow"),
}


def run_classifier(brand: str, urls: list[str], discover: bool, max_results: int) -> dict:
    cmd = [PYTHON, str(PROJECT_ROOT / "classify.py"), "--brand", brand]
    for u in urls:
        cmd += ["--url", u]
    if discover:
        cmd += ["--discover", "--max", str(max_results)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ})
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)
    return json.loads(proc.stdout)


def score_bar(score: int, width: int = 18) -> Text:
    """Render a score as a colored bar from -100 .. +100, centered at 0."""
    s = max(-100, min(100, score))
    half = width // 2
    bar = Text()
    if s >= 0:
        filled = int(round(s / 100 * half))
        bar.append("─" * half, style="grey39")
        bar.append("▓" * filled, style="green")
        bar.append("░" * (half - filled), style="grey39")
    else:
        filled = int(round(-s / 100 * half))
        bar.append("░" * (half - filled), style="grey39")
        bar.append("▓" * filled, style="red")
        bar.append("─" * half, style="grey39")
    return bar


def render_summary(console: Console, data: dict, brand_meta: dict) -> None:
    counts = data["verdict_counts"]
    total = data["candidates_checked"]
    auth, unauth, review = counts["authorized"], counts["unauthorized"], counts["review"]
    title = Text()
    title.append(f"  Brand: ", style="dim")
    title.append(brand_meta["display_name"], style="bold cyan")
    title.append(f"   ·   {total} candidates checked\n\n", style="dim")
    title.append(f"  ✓ {auth} authorized   ", style="bold green")
    title.append(f"✗ {unauth} unauthorized   ", style="bold red")
    title.append(f"? {review} review", style="bold yellow")
    console.print(Panel(title, box=box.HEAVY, border_style="cyan", padding=(0, 1)))


def render_table(console: Console, data: dict) -> None:
    table = Table(
        show_header=True,
        header_style="bold",
        box=box.SIMPLE_HEAVY,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Verdict", width=16)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Bar", width=20)
    table.add_column("Seller", overflow="fold")

    for i, v in enumerate(data["verdicts"], 1):
        label, style = VERDICT_STYLE.get(v["verdict"], (v["verdict"], "white"))
        score = v["score"]
        score_text = Text(f"{score:+4d}", style=style)
        table.add_row(
            str(i),
            Text(label, style=style),
            score_text,
            score_bar(score),
            v.get("seller_host") or v.get("url", ""),
        )
    console.print(table)


def render_details(console: Console, data: dict) -> None:
    for i, v in enumerate(data["verdicts"], 1):
        label, style = VERDICT_STYLE.get(v["verdict"], (v["verdict"], "white"))

        header = Text()
        header.append(f"#{i}  ", style="dim")
        header.append(label + "   ", style=style)
        header.append(f"score {v['score']:+d}", style=style)
        if v.get("fetch_status"):
            header.append(f"   http {v['fetch_status']}", style="dim")

        body_lines: list[Text] = []
        url_line = Text()
        url_line.append("URL: ", style="dim")
        url_line.append(v.get("url", ""), style="cyan")
        body_lines.append(url_line)

        if v.get("reasons"):
            body_lines.append(Text())
            body_lines.append(Text("Reasons:", style="bold"))
            for r in v["reasons"]:
                line = Text("  • ", style="dim")
                line.append(r)
                body_lines.append(line)

        if v.get("evidence"):
            body_lines.append(Text())
            body_lines.append(Text("Evidence:", style="bold"))
            for e in v["evidence"][:6]:
                line = Text("  – ", style="dim")
                line.append(e, style="grey70")
                body_lines.append(line)
            if len(v["evidence"]) > 6:
                body_lines.append(
                    Text(f"  – (+{len(v['evidence']) - 6} more)", style="dim")
                )

        console.print(
            Panel(
                Group(*body_lines),
                title=header,
                title_align="left",
                border_style=style,
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )


def load_brand_meta(brand: str) -> dict:
    profile_path = PROJECT_ROOT / "output" / f"{brand}_profile.json"
    name = brand
    if profile_path.exists():
        try:
            p = json.loads(profile_path.read_text())
            name = p.get("brand", {}).get("name") or p.get("brand", {}).get("trading_names", [brand])[0]
        except Exception:
            pass
    return {"slug": brand, "display_name": name}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--from-file", help="render an existing verdicts JSON instead of running classifier")
    ap.add_argument("--no-details", action="store_true", help="omit per-verdict detail panels")
    args = ap.parse_args()

    if args.from_file:
        data = json.loads(Path(args.from_file).read_text())
    else:
        if not args.url and not args.discover:
            sys.exit("pass --url, --discover, or --from-file")
        data = run_classifier(args.brand, args.url, args.discover, args.max)

    console = Console()
    brand_meta = load_brand_meta(args.brand)

    console.print()
    render_summary(console, data, brand_meta)
    console.print()
    render_table(console, data)
    if not args.no_details:
        console.print(Rule(style="dim"))
        render_details(console, data)
    console.print()


if __name__ == "__main__":
    main()
