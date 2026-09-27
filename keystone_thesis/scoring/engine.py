"""Combine the six components into one auditable score card."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..company import CompanySnapshot, primary_theme
from ..thesis import COMPONENTS, Thesis
from . import components as C

LABELS = {
    "theme_fit": "Theme fit",
    "macro_alignment": "Macro alignment",
    "strategy_fit": "Strategy fit",
    "financial_resilience": "Financial resilience",
    "execution_risk": "Execution risk (inverse)",
    "valuation_tolerance": "Valuation tolerance",
}

SENSITIVITY_DELTAS = (-20, -10, 10, 20)


@dataclass
class ScoreCard:
    ticker: str
    company: str
    thesis_id: str
    thesis_name: str
    overall: float
    band: str
    band_description: str
    components: Dict[str, C.ComponentScore]
    weights: Dict[str, float]
    theme_shares: Dict[str, float]
    primary_theme: Optional[str]
    gates: List[Dict[str, Any]]
    gate_capped: bool
    sensitivity: Dict[str, Dict[str, float]]
    data_coverage: float
    snapshot: CompanySnapshot
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    memo: Optional[str] = None

    @property
    def contributions(self) -> Dict[str, float]:
        return {k: round(self.components[k].score * self.weights[k], 2) for k in COMPONENTS}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company": self.company,
            "thesis": {"id": self.thesis_id, "name": self.thesis_name},
            "overall": round(self.overall, 2),
            "band": self.band,
            "band_description": self.band_description,
            "scores": {k: round(self.components[k].score, 2) for k in COMPONENTS},
            "weights": self.weights,
            "contributions": self.contributions,
            "theme_shares": self.theme_shares,
            "primary_theme": self.primary_theme,
            "gates": self.gates,
            "gate_capped": self.gate_capped,
            "sensitivity": self.sensitivity,
            "data_coverage": round(self.data_coverage, 2),
            "components": {k: self.components[k].to_dict() for k in COMPONENTS},
            "company_data": {"source": self.snapshot.source, "as_of": self.snapshot.as_of,
                             "fictional": self.snapshot.fictional, "units": self.snapshot.units,
                             "currency": self.snapshot.currency},
            "generated_at": self.generated_at,
            "memo": self.memo,
        }


def _weighted(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(scores[k] * weights[k] for k in COMPONENTS)


def sensitivity_table(scores: Dict[str, float], weights: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Overall score if one component moves by +/-10 or +/-20 points (tornado-chart input)."""
    table = {}
    for comp in COMPONENTS:
        row = {}
        for d in SENSITIVITY_DELTAS:
            shifted = dict(scores)
            shifted[comp] = max(0.0, min(100.0, scores[comp] + d))
            row[f"{d:+d}"] = round(_weighted(shifted, weights), 2)
        table[comp] = row
    return table


def score_company(snapshot: CompanySnapshot, thesis: Thesis,
                  theme_override: Optional[Dict[str, float]] = None) -> ScoreCard:
    metrics = snapshot.derived()

    shares = theme_override or C.map_themes(snapshot, thesis)
    theme_id = primary_theme(shares)

    comps = {
        "theme_fit": C.score_theme_fit(snapshot, thesis, shares),
        "macro_alignment": C.score_macro(thesis, theme_id),
        "strategy_fit": C.score_strategy(metrics, thesis),
        "financial_resilience": C.score_resilience(metrics, thesis),
        "execution_risk": C.score_execution(metrics, thesis),
        "valuation_tolerance": C.score_valuation(metrics, thesis),
    }
    scores = {k: comps[k].score for k in COMPONENTS}
    overall = _weighted(scores, thesis.weights)

    gate_rows, capped = [], False
    for g in thesis.gates:
        result = g.condition.evaluate(metrics)
        status = "unknown" if result is None else ("pass" if result else "fail")
        gate_rows.append({"gate": g.name, "rule": g.condition.describe(), "status": status,
                          "value": metrics.get(g.condition.metric)})
        if result is False:
            # A failed deal-breaker always flags the company and caps its score.
            overall, capped = min(overall, thesis.gate_cap), True

    band = thesis.band_for(overall)
    coverage = sum(comps[k].coverage * thesis.weights[k] for k in COMPONENTS)

    return ScoreCard(
        ticker=snapshot.ticker,
        company=snapshot.name,
        thesis_id=thesis.id,
        thesis_name=thesis.name,
        overall=overall,
        band=band.label,
        band_description=band.description,
        components=comps,
        weights=thesis.weights,
        theme_shares={k: round(v, 1) for k, v in shares.items() if v > 0},
        primary_theme=theme_id,
        gates=gate_rows,
        gate_capped=capped,
        sensitivity=sensitivity_table(scores, thesis.weights),
        data_coverage=coverage,
        snapshot=snapshot,
    )
