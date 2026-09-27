"""The six component scorers. Each returns a :class:`ComponentScore` (0-100)
with the inputs it used and a plain-English trace, so every number in a
report can be audited back to the thesis file and the company data.

All of the judgement lives in the thesis YAML; this module only does the maths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..company import CompanySnapshot, primary_theme, text_blob
from ..thesis import Thesis


@dataclass
class ComponentScore:
    score: float
    inputs: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    coverage: float = 1.0  # share of the inputs this component needed that were available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "coverage": round(self.coverage, 2),
            "inputs": self.inputs,
            "notes": self.notes,
        }


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# 1. Theme fit: is the company in the part of the economy the thesis bets on?
# ---------------------------------------------------------------------------

def map_themes(snapshot: CompanySnapshot, thesis: Thesis) -> Dict[str, float]:
    """Return {theme_id: revenue share %} plus '_unmapped'.

    Order of precedence: an explicit analyst override on the snapshot, then
    revenue segments matched by keyword, then the description as a whole.
    """
    if snapshot.themes:
        shares = {k: float(v) for k, v in snapshot.themes.items()}
        shares["_unmapped"] = max(0.0, 100.0 - sum(shares.values()))
        return shares

    def best_theme(text: str) -> Optional[str]:
        text = text.lower()
        hits = [(sum(1 for kw in t.keywords if kw in text), t.id) for t in thesis.themes]
        hits = [h for h in hits if h[0] > 0]
        return max(hits)[1] if hits else None

    shares: Dict[str, float] = {}
    if snapshot.segments:
        for seg in snapshot.segments:
            tid = best_theme(seg.name) or "_unmapped"
            shares[tid] = shares.get(tid, 0.0) + seg.revenue_share_pct
        # If no segment matched, fall back to the whole description.
        if set(shares) == {"_unmapped"}:
            tid = best_theme(text_blob(snapshot))
            if tid:
                shares = {tid: 100.0}
    else:
        tid = best_theme(text_blob(snapshot))
        shares = {tid: 100.0} if tid else {"_unmapped": 100.0}

    shares.setdefault("_unmapped", 0.0)
    return shares


def score_theme_fit(snapshot: CompanySnapshot, thesis: Thesis,
                    shares: Dict[str, float]) -> ComponentScore:
    total = 0.0
    breakdown = []
    for tid, share in shares.items():
        if share <= 0:
            continue
        if tid == "_unmapped":
            necessity, name = thesis.unmapped_theme_score, "Outside the thesis"
        else:
            theme = thesis.theme(tid)
            necessity, name = (theme.necessity, theme.name) if theme else (thesis.unmapped_theme_score, tid)
        total += share * necessity / 100.0
        breakdown.append({"theme": name, "revenue_share_pct": share, "necessity": necessity})

    capped = min(total, thesis.theme_max_score)
    notes = []
    if capped < total:
        notes.append(f"Capped at {thesis.theme_max_score:g} (thesis max_score) from {total:.1f}.")
    unmapped = shares.get("_unmapped", 0.0)
    if unmapped >= 50:
        notes.append(f"{unmapped:.0f}% of revenue sits outside the thesis themes.")
    return ComponentScore(score=_clip(capped), inputs={"themes": breakdown}, notes=notes)


# ---------------------------------------------------------------------------
# 2. Macro alignment: do the macro signals the thesis depends on support it?
# ---------------------------------------------------------------------------

def score_macro(thesis: Thesis, theme_id: Optional[str]) -> ComponentScore:
    signals = [s for s in thesis.macro_signals if s.applies_to(theme_id)]
    if not signals:
        return ComponentScore(score=45.0, coverage=0.0,
                              notes=["No macro signals apply; neutral-low default of 45."])

    weighted, weight_total, low_conf = 0.0, 0.0, False
    rows = []
    for s in signals:
        supports = s.supports()
        # "Improving" depends on the rule: for `below` signals (e.g. inflation) falling is good.
        lower_is_better = "below" in s.supports_when and "above" not in s.supports_when
        improving = s.trend == ("down" if lower_is_better else "up")
        worsening = s.trend == ("up" if lower_is_better else "down")
        if supports and not worsening:
            signal = 1.0
        elif supports:
            signal = 0.5  # tailwind, but fading
        elif improving:
            signal = 0.2  # headwind, but improving
        else:
            signal = 0.0
        low_conf |= s.confidence < 0.5
        weighted += signal * s.confidence
        weight_total += s.confidence
        rows.append({"signal": s.name, "value": s.value, "trend": s.trend,
                     "supports": supports, "credit": signal, "confidence": s.confidence})

    score = (weighted / weight_total) * thesis.macro_max_score if weight_total else 0.0
    notes = []
    if len(signals) < thesis.macro_min_signals:
        score = min(score, 70.0)
        notes.append(f"Only {len(signals)} signals apply; capped at 70 for thin evidence.")
    if low_conf:
        score = min(score, 80.0)
        notes.append("A signal has confidence below 0.5; capped at 80.")
    return ComponentScore(score=_clip(score), inputs={"signals": rows}, notes=notes)


# ---------------------------------------------------------------------------
# 3. Strategy fit: does the company look like the winners the thesis expects?
# ---------------------------------------------------------------------------

def _trait_points(value: float, good: float, bad: float, higher_is_better: bool) -> float:
    if higher_is_better:
        if value >= good:
            return 100.0
        if value <= bad:
            return 0.0
        return (value - bad) / (good - bad) * 100.0
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return (bad - value) / (bad - good) * 100.0


def score_strategy(metrics: Dict[str, Any], thesis: Thesis) -> ComponentScore:
    rows, weighted, used_weight, total_weight = [], 0.0, 0.0, 0.0
    for t in thesis.traits:
        total_weight += t.weight
        value = metrics.get(t.metric)
        if value is None:
            rows.append({"trait": t.name, "metric": t.metric, "value": None, "points": None})
            continue
        pts = _trait_points(float(value), t.good, t.bad, t.higher_is_better)
        weighted += pts * t.weight
        used_weight += t.weight
        rows.append({"trait": t.name, "metric": t.metric, "value": value, "points": round(pts, 1)})

    coverage = used_weight / total_weight if total_weight else 0.0
    notes = []
    if used_weight == 0:
        return ComponentScore(score=40.0, inputs={"traits": rows}, coverage=0.0,
                              notes=["No trait data available; conservative default of 40."])
    score = weighted / used_weight
    if coverage < thesis.trait_min_coverage:
        # Missing data pulls the score toward a neutral 50 instead of rewarding gaps.
        score = coverage * score + (1 - coverage) * 50.0
        notes.append(f"Only {coverage:.0%} of trait weight had data; blended toward 50.")
    return ComponentScore(score=_clip(score), inputs={"traits": rows}, coverage=coverage, notes=notes)


# ---------------------------------------------------------------------------
# 4. Financial resilience: how long does the company survive the stress cases?
# ---------------------------------------------------------------------------

REQUIRED_FOR_STRESS = ("revenue_ltm", "ebitda_margin", "cash", "total_debt", "interest_expense", "capex")


def survival_months(metrics: Dict[str, Any], scenario, thesis: Thesis) -> Tuple[float, Dict[str, float]]:
    revenue = metrics["revenue_ltm"] * (1 + scenario.revenue_shock_pct / 100.0)
    margin = metrics["ebitda_margin"] / 100.0 + scenario.margin_change_bps / 10000.0
    ebitda = revenue * margin
    interest = metrics["interest_expense"]
    tax = max(0.0, ebitda - interest) * thesis.tax_rate
    capex = metrics["capex"] * (1 - scenario.capex_cut_pct / 100.0)
    debt_due = metrics.get("debt_due_12m") or 0.0
    annual_fcf = ebitda - interest - tax - capex - debt_due
    liquidity = metrics["cash"] + (metrics.get("undrawn_credit") or 0.0)

    if annual_fcf >= 0:
        months = thesis.max_survival_months
    elif liquidity <= 0:
        months = 0.0
    else:
        months = min(thesis.max_survival_months, liquidity / (-annual_fcf / 12.0))
    detail = {"stressed_revenue": revenue, "stressed_ebitda": ebitda,
              "annual_fcf": annual_fcf, "liquidity": liquidity}
    return months, {k: round(v, 1) for k, v in detail.items()}


def _curve_score(months: float, curve: List[Dict[str, float]]) -> float:
    # curve is sorted by min_months descending; interpolate inside the band.
    for band in curve:
        lo = band["min_months"]
        if months >= lo:
            hi = band.get("max_months")
            s_lo, s_hi = band["score"]
            if hi is None or hi <= lo:
                return float(s_lo)
            frac = min(1.0, (months - lo) / (hi - lo))
            return s_lo + frac * (s_hi - s_lo)
    return 0.0


def score_resilience(metrics: Dict[str, Any], thesis: Thesis) -> ComponentScore:
    missing = [k for k in REQUIRED_FOR_STRESS if metrics.get(k) is None]
    if missing:
        return ComponentScore(
            score=40.0, coverage=1 - len(missing) / len(REQUIRED_FOR_STRESS),
            inputs={"missing": missing},
            notes=[f"Stress test skipped, missing {', '.join(missing)}; conservative default of 40."],
        )

    results = {}
    for sc in thesis.scenarios:
        months, detail = survival_months(metrics, sc, thesis)
        results[sc.id] = {"name": sc.name, "survival_months": round(months, 1), **detail}

    if thesis.score_scenario == "worst":
        scored_id = min(results, key=lambda k: results[k]["survival_months"])
    else:
        scored_id = thesis.score_scenario
    months = results[scored_id]["survival_months"]
    base = _curve_score(months, thesis.survival_curve)

    lev = metrics.get("net_debt_ebitda")
    adjustment = 0.0
    if lev is not None:
        for bracket in thesis.leverage_adjustment:
            cap = bracket.get("max_net_debt_ebitda")
            if cap is None or lev <= cap:
                adjustment = float(bracket["adjust"])
                break
    elif metrics.get("ebitda", 0) <= 0:
        adjustment = -25.0  # negative EBITDA: leverage is effectively unbounded

    score = min(base + adjustment, thesis.resilience_max_score)
    notes = [f"Scored on '{results[scored_id]['name']}': {months:g} months of runway."]
    if base + adjustment > thesis.resilience_max_score:
        notes.append(f"Capped at {thesis.resilience_max_score:g}; unknown risks always exist.")
    return ComponentScore(
        score=_clip(score),
        inputs={"scenarios": results, "scored_scenario": scored_id, "base_score": round(base, 1),
                "net_debt_ebitda": None if lev is None else round(lev, 2),
                "leverage_adjustment": adjustment},
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 5. Execution risk (inverse): start high, subtract every red flag that fires
# ---------------------------------------------------------------------------

def score_execution(metrics: Dict[str, Any], thesis: Thesis) -> ComponentScore:
    score = thesis.execution_base_score
    fired, unknown = [], []
    for flag in thesis.red_flags:
        result = flag.condition.evaluate(metrics)
        if result is None:
            unknown.append(flag.name)
        elif result:
            score -= flag.penalty
            fired.append({"flag": flag.name, "rule": flag.condition.describe(),
                          "value": metrics.get(flag.condition.metric), "penalty": flag.penalty})

    checked = len(thesis.red_flags) - len(unknown)
    coverage = checked / len(thesis.red_flags) if thesis.red_flags else 1.0
    notes = []
    if coverage < 0.5:
        # Absence of evidence is not evidence of absence.
        score = min(score, thesis.execution_unknown_cap)
        notes.append(f"Only {checked}/{len(thesis.red_flags)} red flags could be checked; "
                     f"capped at {thesis.execution_unknown_cap:g}.")
    return ComponentScore(score=_clip(score), coverage=coverage,
                          inputs={"fired": fired, "unchecked": unknown}, notes=notes)


# ---------------------------------------------------------------------------
# 6. Valuation tolerance: how much growth is already in the price?
# ---------------------------------------------------------------------------

def implied_growth(pe: float, r: float, years: int, terminal_g: float) -> float:
    """Two-stage reverse DCF on earnings: the annual growth over ``years`` that,
    followed by ``terminal_g`` forever, makes discounted earnings equal the P/E.
    Rates are decimals. Solved by bisection; clipped to [-50%, +100%]."""
    def value(g: float) -> float:
        v, f = 0.0, 1.0
        for _ in range(years):
            f *= (1 + g) / (1 + r)
            v += f
        return v + f * (1 + terminal_g) / (r - terminal_g)

    lo, hi = -0.5, 1.0
    if value(lo) >= pe:
        return lo
    if value(hi) <= pe:
        return hi
    for _ in range(80):
        mid = (lo + hi) / 2
        if value(mid) < pe:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def score_valuation(metrics: Dict[str, Any], thesis: Thesis) -> ComponentScore:
    """Reverse DCF. Solve for the earnings growth the current P/E is paying for
    (two stages: ``stage_years`` of growth, then ``terminal_growth_pct``),
    and compare it with the growth the company has actually delivered, capped
    by the thesis. The more the price asks for beyond that, the less room there
    is for error, and the lower the score.
    """
    pe = metrics.get("pe")
    if pe is None:
        return ComponentScore(score=40.0, coverage=0.0, notes=["No P/E available; neutral-low default of 40."])
    if pe <= 0:
        return ComponentScore(score=thesis.loss_making_score, inputs={"pe": pe},
                              notes=["Loss-making: the price has no earnings support."])

    r = thesis.cost_of_equity_pct
    implied = implied_growth(float(pe), r / 100.0, thesis.stage_years, thesis.terminal_growth_pct / 100.0) * 100
    delivered = metrics.get("revenue_cagr_3y")
    expected = min(float(delivered), thesis.growth_cap_pct) if delivered is not None else thesis.growth_cap_pct / 2
    gap = implied - expected

    score, label = thesis.valuation_brackets[-1]["score"], thesis.valuation_brackets[-1].get("label", "")
    for b in thesis.valuation_brackets:
        cap = b.get("max_gap_pp")
        if cap is None or gap <= cap:
            score, label = b["score"], b.get("label", "")
            break
    return ComponentScore(
        score=_clip(float(score)),
        inputs={"pe": pe, "cost_of_equity_pct": r, "stage_years": thesis.stage_years,
                "terminal_growth_pct": thesis.terminal_growth_pct,
                "implied_growth_pct": round(implied, 2), "expected_growth_pct": round(expected, 2),
                "gap_pp": round(gap, 2)},
        notes=[label] if label else [],
    )
