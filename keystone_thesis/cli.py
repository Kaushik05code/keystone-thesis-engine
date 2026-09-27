"""Command line interface.

    keystone list
    keystone score ADSL --thesis india_structural_growth
    keystone score HAL.NS --thesis india_structural_growth --provider yahoo --out reports/
    keystone rank --thesis quality_compounders
    keystone compare ADSL --theses india_structural_growth quality_compounders
    keystone validate theses/my_thesis.yaml
    keystone new-thesis my_thesis
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List

from . import __version__
from .providers import ProviderError, get_provider
from .report import render_html, render_leaderboard, render_scorecard
from .scoring import LABELS, ScoreCard, score_company
from .thesis import COMPONENTS, ThesisError, load_thesis, resolve_thesis_path

ROOT = Path(__file__).resolve().parent.parent


def _bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _summary(card: ScoreCard) -> str:
    lines = [f"{card.company} ({card.ticker})  vs  {card.thesis_name}",
             f"Overall {card.overall:.1f} / 100 · {card.band}"
             + ("  [capped by a deal-breaker]" if card.gate_capped else "")]
    for k in COMPONENTS:
        sc = card.components[k].score
        lines.append(f"  {LABELS[k]:<26} {sc:5.1f}  {_bar(sc)}  ×{card.weights[k]:.0%}")
    lines.append(f"  Data coverage {card.data_coverage:.0%}"
                 + (" · fictional sample company" if card.snapshot.fictional else ""))
    return "\n".join(lines)


def _theses_dir() -> Path:
    local = Path.cwd() / "theses"
    return local if local.exists() else ROOT / "theses"


def _score(ticker: str, thesis, provider, use_llm: bool, memo: bool) -> ScoreCard:
    snap = provider.get(ticker)
    override = None
    client = None
    if use_llm or memo:
        from .agents import LLMClient, map_themes_with_llm, write_memo  # noqa: F401

        client = LLMClient()
    if use_llm:
        from .agents import map_themes_with_llm
        from .scoring.components import map_themes

        if map_themes(snap, thesis).get("_unmapped", 0) >= 50:
            override = map_themes_with_llm(snap, thesis, client)
    card = score_company(snap, thesis, theme_override=override)
    if memo:
        from .agents import write_memo

        card.memo = write_memo(card, thesis, client)
    return card


def _write(card: ScoreCard, out_dir: Path, fmt: str) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{card.ticker.replace('.', '_')}__{card.thesis_id}"
    written = []
    formats = ["md", "html", "json"] if fmt == "all" else [fmt]
    for f in formats:
        path = out_dir / f"{stem}.{f}"
        if f == "md":
            path.write_text(render_scorecard(card), encoding="utf-8")
        elif f == "html":
            path.write_text(render_html(card), encoding="utf-8")
        elif f == "json":
            path.write_text(json.dumps(card.to_dict(), indent=2, default=str), encoding="utf-8")
        written.append(path)
    return written


def cmd_score(args) -> int:
    thesis = load_thesis(args.thesis)
    provider = get_provider(args.provider, **({"data_dir": args.data_dir} if args.provider == "sample" else {}))
    for ticker in args.tickers:
        card = _score(ticker, thesis, provider, args.llm, args.memo)
        if args.out:
            for p in _write(card, Path(args.out), args.format or "all"):
                print(f"wrote {p}")
        elif args.format == "md":
            print(render_scorecard(card))
        elif args.format == "json":
            print(json.dumps(card.to_dict(), indent=2, default=str))
        elif args.format == "html":
            print(render_html(card))
        else:
            print(_summary(card))
            print()
    return 0


def cmd_rank(args) -> int:
    thesis = load_thesis(args.thesis)
    provider = get_provider(args.provider, **({"data_dir": args.data_dir} if args.provider == "sample" else {}))
    tickers = args.tickers or provider.available()
    if not tickers:
        print("No tickers given and the provider cannot list any.", file=sys.stderr)
        return 2
    cards = [score_company(provider.get(t), thesis) for t in tickers]
    board = render_leaderboard(cards, thesis.name)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(board, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(board)
    return 0


def cmd_compare(args) -> int:
    provider = get_provider(args.provider, **({"data_dir": args.data_dir} if args.provider == "sample" else {}))
    snap = provider.get(args.ticker)
    theses = args.theses or sorted(p.stem for p in _theses_dir().glob("*.yaml") if not p.stem.startswith("_"))
    header = "| Thesis | Overall | Band | " + " | ".join(LABELS[k] for k in COMPONENTS) + " |"
    print(f"# {snap.name} ({snap.ticker}) under different theses\n")
    print(header)
    print("|---|---:|---|" + "---:|" * len(COMPONENTS))
    for name in theses:
        thesis = load_thesis(name)
        card = score_company(snap, thesis)
        cells = " | ".join(f"{card.components[k].score:.0f}" for k in COMPONENTS)
        print(f"| {thesis.name} | **{card.overall:.1f}** | {card.band} | {cells} |")
    return 0


def cmd_validate(args) -> int:
    status = 0
    for path in args.files:
        try:
            t = load_thesis(path)
            print(f"OK    {path}  ({t.name}: {len(t.themes)} themes, {len(t.macro_signals)} macro signals, "
                  f"{len(t.traits)} traits, {len(t.red_flags)} red flags, {len(t.gates)} gates)")
        except (ThesisError, OSError, KeyError, TypeError, ValueError) as exc:
            print(f"FAIL  {path}: {exc}")
            status = 1
    return status


def cmd_new(args) -> int:
    dest = Path.cwd() / "theses" / f"{args.name}.yaml"
    if dest.exists():
        print(f"{dest} already exists", file=sys.stderr)
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(resolve_thesis_path("_template"), dest)
    text = dest.read_text(encoding="utf-8").replace("id: my_thesis", f"id: {args.name}", 1)
    dest.write_text(text, encoding="utf-8")
    print(f"created {dest}\nedit it, then run: keystone validate {dest}")
    return 0


def cmd_list(args) -> int:
    print("Theses:")
    for p in sorted(_theses_dir().glob("*.yaml")):
        if p.stem.startswith("_"):
            continue
        try:
            print(f"  {p.stem:<28} {load_thesis(str(p)).name}")
        except ThesisError as exc:
            print(f"  {p.stem:<28} INVALID: {exc}")
    try:
        sample = get_provider("sample", data_dir=args.data_dir)
        print("\nSample companies (fictional):")
        for t in sample.available():
            snap = sample.get(t)
            print(f"  {t:<10} {snap.name}")
    except ProviderError as exc:
        print(f"\n{exc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="keystone", description="Score companies against an investment thesis you write in YAML.")
    p.add_argument("--version", action="version", version=f"keystone {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def data_opts(sp):
        sp.add_argument("--provider", default="sample", choices=["sample", "yahoo"],
                        help="where company data comes from (default: bundled fictional samples)")
        sp.add_argument("--data-dir", help="folder of JSON snapshots for the sample provider")

    s = sub.add_parser("score", help="score one or more companies")
    s.add_argument("tickers", nargs="+")
    s.add_argument("--thesis", "-t", required=True, help="thesis name in ./theses or a path to a YAML file")
    s.add_argument("--format", "-f", choices=["md", "html", "json", "all"], help="print or write this format")
    s.add_argument("--out", "-o", help="write reports to this folder instead of printing")
    s.add_argument("--llm", action="store_true", help="use an LLM to map themes when keywords miss")
    s.add_argument("--memo", action="store_true", help="add an LLM-written investment memo")
    data_opts(s)
    s.set_defaults(func=cmd_score)

    r = sub.add_parser("rank", help="rank many companies against one thesis")
    r.add_argument("--thesis", "-t", required=True)
    r.add_argument("--tickers", nargs="*")
    r.add_argument("--out", "-o", help="write the leaderboard to this Markdown file")
    data_opts(r)
    r.set_defaults(func=cmd_rank)

    c = sub.add_parser("compare", help="score one company under several theses")
    c.add_argument("ticker")
    c.add_argument("--theses", nargs="*", help="default: every thesis in ./theses")
    data_opts(c)
    c.set_defaults(func=cmd_compare)

    v = sub.add_parser("validate", help="check thesis files for errors")
    v.add_argument("files", nargs="+")
    v.set_defaults(func=cmd_validate)

    n = sub.add_parser("new-thesis", help="start a new thesis from the commented template")
    n.add_argument("name")
    n.set_defaults(func=cmd_new)

    ls = sub.add_parser("list", help="list theses and sample companies")
    ls.add_argument("--data-dir")
    ls.set_defaults(func=cmd_list)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ThesisError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
