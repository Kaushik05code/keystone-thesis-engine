"""Render a score card (or a leaderboard) as Markdown."""

from __future__ import annotations

from typing import List

from ..scoring import LABELS, ScoreCard
from ..thesis import COMPONENTS


def _bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v)


def render_scorecard(card: ScoreCard) -> str:
    snap = card.snapshot
    out: List[str] = []
    out.append(f"# {card.company} ({card.ticker})")
    out.append(f"**Thesis:** {card.thesis_name}  ")
    out.append(f"**Overall score:** **{card.overall:.1f} / 100**, {card.band}  ")
    if card.band_description:
        out.append(f"_{card.band_description}_  ")
    out.append(f"**Data coverage:** {card.data_coverage:.0%} · **Data:** {snap.source or 'n/a'}"
               f"{' · FICTIONAL SAMPLE COMPANY' if snap.fictional else ''} · as of {snap.as_of or 'n/a'}")
    if card.gate_capped:
        out.append("\n> A deal-breaker gate failed, so the overall score is capped. See *Deal-breakers* below.")

    out.append("\n## Score breakdown\n")
    out.append("| Component | Score | Weight | Contribution | |")
    out.append("|---|---:|---:|---:|---|")
    for k in COMPONENTS:
        c = card.components[k]
        out.append(f"| {LABELS[k]} | {c.score:.1f} | {card.weights[k]:.0%} | "
                   f"{card.contributions[k]:.1f} | `{_bar(c.score)}` |")

    th = card.components["theme_fit"]
    out.append("\n## 1. Theme fit\n")
    out.append("| Theme | Revenue share | Necessity |")
    out.append("|---|---:|---:|")
    for row in th.inputs.get("themes", []):
        out.append(f"| {row['theme']} | {row['revenue_share_pct']:.0f}% | {row['necessity']:.0f} |")

    mac = card.components["macro_alignment"]
    out.append("\n## 2. Macro alignment\n")
    if mac.inputs.get("signals"):
        out.append("| Signal | Value | Trend | Supports thesis | Credit |")
        out.append("|---|---:|---|---|---:|")
        for s in mac.inputs["signals"]:
            out.append(f"| {s['signal']} | {_fmt(s['value'])} | {s['trend']} | "
                       f"{'yes' if s['supports'] else 'no'} | {s['credit']:.1f} |")

    st = card.components["strategy_fit"]
    out.append("\n## 3. Strategy fit (does it look like a future winner?)\n")
    out.append("| Trait | Metric | Value | Points |")
    out.append("|---|---|---:|---:|")
    for t in st.inputs.get("traits", []):
        out.append(f"| {t['trait']} | `{t['metric']}` | {_fmt(t['value'])} | {_fmt(t['points'])} |")

    res = card.components["financial_resilience"]
    out.append("\n## 4. Financial resilience (stress test)\n")
    if res.inputs.get("scenarios"):
        out.append(f"| Scenario | Stressed revenue | Stressed EBITDA | Annual FCF | Runway (months) |")
        out.append("|---|---:|---:|---:|---:|")
        for sid, s in res.inputs["scenarios"].items():
            mark = " ◀ scored" if sid == res.inputs.get("scored_scenario") else ""
            out.append(f"| {s['name']}{mark} | {_fmt(s['stressed_revenue'])} | {_fmt(s['stressed_ebitda'])} | "
                       f"{_fmt(s['annual_fcf'])} | {_fmt(s['survival_months'])} |")
        out.append(f"\nNet debt / EBITDA: {_fmt(res.inputs.get('net_debt_ebitda'))} "
                   f"(adjustment {res.inputs.get('leverage_adjustment', 0):+g}). Figures in {snap.currency} {snap.units}.")

    exe = card.components["execution_risk"]
    out.append("\n## 5. Execution risk (red flags)\n")
    fired = exe.inputs.get("fired", [])
    if fired:
        out.append("| Red flag | Rule | Value | Penalty |")
        out.append("|---|---|---:|---:|")
        for f in fired:
            out.append(f"| {f['flag']} | `{f['rule']}` | {_fmt(f['value'])} | -{f['penalty']:g} |")
    else:
        out.append("No red flags fired.")
    if exe.inputs.get("unchecked"):
        out.append(f"\nCould not check (no data): {', '.join(exe.inputs['unchecked'])}.")

    val = card.components["valuation_tolerance"]
    out.append("\n## 6. Valuation tolerance (reverse DCF)\n")
    vi = val.inputs
    if "implied_growth_pct" in vi:
        out.append(f"At a P/E of {vi['pe']:.1f} and a {vi['cost_of_equity_pct']:g}% cost of equity, the price needs "
                   f"~{vi['implied_growth_pct']:.1f}% earnings growth a year for {vi['stage_years']} years "
                   f"(then {vi['terminal_growth_pct']:g}% forever). The company has delivered "
                   f"~{vi['expected_growth_pct']:.1f}% (capped by the thesis): a gap of {vi['gap_pp']:+.1f} pp.")

    if card.gates:
        out.append("\n## Deal-breakers (gates)\n")
        out.append("| Gate | Rule | Value | Status |")
        out.append("|---|---|---:|---|")
        for g in card.gates:
            out.append(f"| {g['gate']} | `{g['rule']}` | {_fmt(g['value'])} | {g['status']} |")

    out.append("\n## Sensitivity (overall score if one component moves)\n")
    out.append("| Component | -20 | -10 | +10 | +20 |")
    out.append("|---|---:|---:|---:|---:|")
    for k in COMPONENTS:
        row = card.sensitivity[k]
        out.append(f"| {LABELS[k]} | {row['-20']:.1f} | {row['-10']:.1f} | {row['+10']:.1f} | {row['+20']:.1f} |")

    notes = [(LABELS[k], n) for k in COMPONENTS for n in card.components[k].notes]
    if notes:
        out.append("\n## Engine notes\n")
        out += [f"- **{label}:** {n}" for label, n in notes]

    if card.memo:
        out.append("\n## Analyst memo (LLM-written from the numbers above)\n")
        out.append(card.memo)

    out.append(f"\n---\n_Generated {card.generated_at} by Keystone Thesis Engine. Not investment advice._\n")
    return "\n".join(out)


def render_leaderboard(cards: List[ScoreCard], thesis_name: str) -> str:
    cards = sorted(cards, key=lambda c: c.overall, reverse=True)
    out = [f"# Leaderboard: {thesis_name}\n",
           "| # | Company | Overall | Band | Theme | Macro | Strategy | Resilience | Execution | Valuation |",
           "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for i, c in enumerate(cards, 1):
        s = {k: c.components[k].score for k in COMPONENTS}
        flag = " ⛔" if c.gate_capped else ""
        out.append(f"| {i} | {c.company} ({c.ticker}){flag} | **{c.overall:.1f}** | {c.band} | "
                   f"{s['theme_fit']:.0f} | {s['macro_alignment']:.0f} | {s['strategy_fit']:.0f} | "
                   f"{s['financial_resilience']:.0f} | {s['execution_risk']:.0f} | {s['valuation_tolerance']:.0f} |")
    if any(c.gate_capped for c in cards):
        out.append("\n⛔ = failed a deal-breaker gate; overall capped.")
    return "\n".join(out) + "\n"
