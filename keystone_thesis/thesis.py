"""Load and validate an investment thesis written in YAML.

A thesis is the only thing you need to edit to make the engine yours. It
declares where you think value will be created (themes), which macro signals
your view depends on, what a winning company looks like, how hard to stress
the balance sheet, which red flags you refuse to ignore, how much valuation
risk you accept, and how the six component scores are weighted.

See ``theses/_template.yaml`` for a fully commented example.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

COMPONENTS = (
    "theme_fit",
    "macro_alignment",
    "strategy_fit",
    "financial_resilience",
    "execution_risk",
    "valuation_tolerance",
)


class ThesisError(ValueError):
    """Raised when a thesis file is missing fields or internally inconsistent."""


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

@dataclass
class Condition:
    """A test on one company metric: ``above``, ``below`` or ``equals``."""

    metric: str
    above: Optional[float] = None
    below: Optional[float] = None
    equals: Any = None

    def evaluate(self, metrics: Dict[str, Any]) -> Optional[bool]:
        """True/False if the metric is known, None if the company lacks the data."""
        value = metrics.get(self.metric)
        if value is None:
            return None
        if self.equals is not None:
            return value == self.equals
        if self.above is not None and not float(value) > self.above:
            return False
        if self.below is not None and not float(value) < self.below:
            return False
        return True

    def describe(self) -> str:
        if self.equals is not None:
            return f"{self.metric} = {self.equals}"
        parts = []
        if self.above is not None:
            parts.append(f"{self.metric} > {self.above:g}")
        if self.below is not None:
            parts.append(f"{self.metric} < {self.below:g}")
        return " and ".join(parts)


@dataclass
class Theme:
    id: str
    name: str
    necessity: float
    keywords: List[str]


@dataclass
class MacroSignal:
    id: str
    name: str
    value: float
    trend: str
    confidence: float
    supports_when: Dict[str, float]
    themes: List[str]

    def supports(self) -> bool:
        above = self.supports_when.get("above")
        below = self.supports_when.get("below")
        ok = True
        if above is not None:
            ok = ok and self.value > above
        if below is not None:
            ok = ok and self.value < below
        return ok

    def applies_to(self, theme_id: Optional[str]) -> bool:
        return "all" in self.themes or (theme_id is not None and theme_id in self.themes)


@dataclass
class Trait:
    id: str
    name: str
    metric: str
    good: float
    bad: float
    weight: float
    higher_is_better: bool = True


@dataclass
class StressScenario:
    id: str
    name: str
    revenue_shock_pct: float
    margin_change_bps: float
    capex_cut_pct: float = 0.0


@dataclass
class RedFlag:
    id: str
    name: str
    condition: Condition
    penalty: float


@dataclass
class Gate:
    id: str
    name: str
    condition: Condition


@dataclass
class Band:
    min: float
    label: str
    description: str = ""


@dataclass
class Thesis:
    id: str
    name: str
    summary: str
    author: str
    as_of: str
    horizon_years: int
    weights: Dict[str, float]
    themes: List[Theme]
    unmapped_theme_score: float
    theme_max_score: float
    macro_signals: List[MacroSignal]
    macro_max_score: float
    macro_min_signals: int
    traits: List[Trait]
    trait_min_coverage: float
    scenarios: List[StressScenario]
    score_scenario: str
    tax_rate: float
    max_survival_months: float
    resilience_max_score: float
    survival_curve: List[Dict[str, float]]
    leverage_adjustment: List[Dict[str, Optional[float]]]
    execution_base_score: float
    execution_unknown_cap: float
    red_flags: List[RedFlag]
    cost_of_equity_pct: float
    stage_years: int
    terminal_growth_pct: float
    growth_cap_pct: float
    loss_making_score: float
    valuation_brackets: List[Dict[str, Any]]
    gates: List[Gate]
    gate_cap: float
    bands: List[Band]
    source_path: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    def theme(self, theme_id: str) -> Optional[Theme]:
        return next((t for t in self.themes if t.id == theme_id), None)

    def band_for(self, score: float) -> Band:
        for band in sorted(self.bands, key=lambda b: b.min, reverse=True):
            if score >= band.min:
                return band
        return self.bands[-1]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _req(section: Dict[str, Any], key: str, where: str) -> Any:
    if key not in section or section[key] is None:
        raise ThesisError(f"'{where}.{key}' is required")
    return section[key]


def _condition(spec: Dict[str, Any], where: str) -> Condition:
    metric = _req(spec, "metric", where)
    cond = Condition(
        metric=metric,
        above=spec.get("above"),
        below=spec.get("below"),
        equals=spec.get("equals"),
    )
    if cond.above is None and cond.below is None and cond.equals is None:
        raise ThesisError(f"'{where}' needs one of above / below / equals")
    return cond


def parse_thesis(data: Dict[str, Any], source_path: Optional[str] = None) -> Thesis:
    """Turn the YAML dictionary into a validated :class:`Thesis`."""
    meta = _req(data, "thesis", "root")
    weights = {k: float(v) for k, v in _req(data, "weights", "root").items()}

    missing = [c for c in COMPONENTS if c not in weights]
    unknown = [k for k in weights if k not in COMPONENTS]
    if missing:
        raise ThesisError(f"weights missing components: {', '.join(missing)}")
    if unknown:
        raise ThesisError(f"unknown weight keys: {', '.join(unknown)}")
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        raise ThesisError(f"weights must sum to 1.0 (they sum to {total:.3f})")

    themes_sec = _req(data, "themes", "root")
    themes = [
        Theme(
            id=_req(t, "id", "themes.list[]"),
            name=t.get("name", t["id"]),
            necessity=float(_req(t, "necessity", f"themes.{t['id']}")),
            keywords=[k.lower() for k in t.get("keywords", [])],
        )
        for t in _req(themes_sec, "list", "themes")
    ]
    theme_ids = {t.id for t in themes}

    macro_sec = data.get("macro", {}) or {}
    signals = []
    for s in macro_sec.get("signals", []) or []:
        applies = s.get("themes", ["all"])
        bad = [t for t in applies if t != "all" and t not in theme_ids]
        if bad:
            raise ThesisError(f"macro signal '{s.get('id')}' references unknown themes: {bad}")
        trend = s.get("trend", "flat")
        if trend not in ("up", "flat", "down"):
            raise ThesisError(f"macro signal '{s.get('id')}' trend must be up / flat / down")
        signals.append(
            MacroSignal(
                id=_req(s, "id", "macro.signals[]"),
                name=s.get("name", s["id"]),
                value=float(_req(s, "value", f"macro.{s['id']}")),
                trend=trend,
                confidence=float(s.get("confidence", 0.8)),
                supports_when=_req(s, "supports_when", f"macro.{s['id']}"),
                themes=applies,
            )
        )

    strat_sec = _req(data, "strategy", "root")
    traits = [
        Trait(
            id=_req(t, "id", "strategy.traits[]"),
            name=t.get("name", t["id"]),
            metric=_req(t, "metric", f"strategy.{t['id']}"),
            good=float(_req(t, "good", f"strategy.{t['id']}")),
            bad=float(_req(t, "bad", f"strategy.{t['id']}")),
            weight=float(t.get("weight", 1.0)),
            higher_is_better=bool(t.get("higher_is_better", True)),
        )
        for t in _req(strat_sec, "traits", "strategy")
    ]
    if not traits:
        raise ThesisError("strategy.traits needs at least one trait")

    res_sec = _req(data, "resilience", "root")
    scenarios = [
        StressScenario(
            id=_req(s, "id", "resilience.scenarios[]"),
            name=s.get("name", s["id"]),
            revenue_shock_pct=float(s.get("revenue_shock_pct", 0)),
            margin_change_bps=float(s.get("margin_change_bps", 0)),
            capex_cut_pct=float(s.get("capex_cut_pct", 0)),
        )
        for s in _req(res_sec, "scenarios", "resilience")
    ]
    score_on = res_sec.get("score_on", "worst")
    if score_on != "worst" and score_on not in {s.id for s in scenarios}:
        raise ThesisError(f"resilience.score_on '{score_on}' is not a scenario id or 'worst'")

    exe_sec = data.get("execution", {}) or {}
    flags = [
        RedFlag(
            id=_req(f, "id", "execution.red_flags[]"),
            name=f.get("name", f["id"]),
            condition=_condition(f, f"execution.{f['id']}"),
            penalty=float(_req(f, "penalty", f"execution.{f['id']}")),
        )
        for f in exe_sec.get("red_flags", []) or []
    ]

    val_sec = _req(data, "valuation", "root")
    if float(val_sec.get("terminal_growth_pct", 5)) >= float(val_sec.get("cost_of_equity_pct", 0)):
        raise ThesisError("valuation.terminal_growth_pct must be below cost_of_equity_pct")
    brackets = sorted(
        _req(val_sec, "brackets", "valuation"),
        key=lambda b: float("inf") if b.get("max_gap_pp") is None else b["max_gap_pp"],
    )

    gate_sec = data.get("gates", {}) or {}
    gates = [
        Gate(id=_req(g, "id", "gates.rules[]"), name=g.get("name", g["id"]),
             condition=_condition(g, f"gates.{g['id']}"))
        for g in gate_sec.get("rules", []) or []
    ]

    bands = [
        Band(min=float(b["min"]), label=b["label"], description=b.get("description", ""))
        for b in _req(data, "bands", "root")
    ]

    return Thesis(
        id=_req(meta, "id", "thesis"),
        name=_req(meta, "name", "thesis"),
        summary=str(meta.get("summary", "")).strip(),
        author=meta.get("author", ""),
        as_of=str(meta.get("as_of", "")),
        horizon_years=int(meta.get("horizon_years", 10)),
        weights=weights,
        themes=themes,
        unmapped_theme_score=float(themes_sec.get("unmapped_score", 25)),
        theme_max_score=float(themes_sec.get("max_score", 100)),
        macro_signals=signals,
        macro_max_score=float(macro_sec.get("max_score", 85)),
        macro_min_signals=int(macro_sec.get("min_signals_for_full_credit", 4)),
        traits=traits,
        trait_min_coverage=float(strat_sec.get("min_coverage", 0.6)),
        scenarios=scenarios,
        score_scenario=score_on,
        tax_rate=float(res_sec.get("tax_rate", 0.25)),
        max_survival_months=float(res_sec.get("max_months", 60)),
        resilience_max_score=float(res_sec.get("max_score", 90)),
        survival_curve=sorted(_req(res_sec, "survival_curve", "resilience"),
                              key=lambda b: b["min_months"], reverse=True),
        leverage_adjustment=res_sec.get("leverage_adjustment", []) or [],
        execution_base_score=float(exe_sec.get("base_score", 90)),
        execution_unknown_cap=float(exe_sec.get("unknown_cap", 70)),
        red_flags=flags,
        cost_of_equity_pct=float(_req(val_sec, "cost_of_equity_pct", "valuation")),
        stage_years=int(val_sec.get("stage_years", 10)),
        terminal_growth_pct=float(val_sec.get("terminal_growth_pct", 5)),
        growth_cap_pct=float(val_sec.get("growth_cap_pct", 15)),
        loss_making_score=float(val_sec.get("loss_making_score", 10)),
        valuation_brackets=brackets,
        gates=gates,
        gate_cap=float(gate_sec.get("cap", 40)),
        bands=bands,
        source_path=source_path,
        raw=data,
    )


def resolve_thesis_path(name_or_path: str) -> Path:
    """Accept a file path or a short name like ``india_structural_growth``."""
    p = Path(name_or_path)
    if p.exists():
        return p
    candidates = [
        Path.cwd() / "theses" / f"{name_or_path}.yaml",
        Path(__file__).resolve().parent.parent / "theses" / f"{name_or_path}.yaml",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise ThesisError(f"thesis '{name_or_path}' not found (looked in ./theses/)")


def load_thesis(name_or_path: str) -> Thesis:
    path = resolve_thesis_path(name_or_path)
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ThesisError(f"{path} is not a YAML mapping")
    return parse_thesis(data, source_path=str(path))
