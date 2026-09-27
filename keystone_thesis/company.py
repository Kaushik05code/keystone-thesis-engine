"""A normalised snapshot of one company, the only input the scorer needs.

Every data provider (bundled samples, Yahoo Finance, or one you write) returns
a :class:`CompanySnapshot`. Money values are in a single unit per snapshot
(``units``, e.g. INR crore). Percentages are plain numbers (21.5 means 21.5%).

Metric keys the default theses read
------------------------------------
revenue_ltm, revenue_cagr_3y, ebitda_margin, roce, cash, total_debt,
interest_expense, capex, debt_due_12m, undrawn_credit, pe,
rnd_pct_revenue, export_share_pct, promoter_holding_pct, promoter_pledge_pct,
top_customer_share_pct, receivable_days, auditor_changes_3y,
related_party_revenue_pct, fcf_conversion_pct

Any metric can be missing; the engine records what it could not check and
lowers its confidence instead of guessing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Segment:
    name: str
    revenue_share_pct: float


@dataclass
class CompanySnapshot:
    ticker: str
    name: str
    sector: str = ""
    industry: str = ""
    description: str = ""
    exchange: str = ""
    currency: str = "INR"
    units: str = "crore"
    as_of: str = ""
    fictional: bool = False
    source: str = ""
    segments: List[Segment] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    # Optional analyst override: {theme_id: relevance_pct}
    themes: Dict[str, float] = field(default_factory=dict)

    # ---- derived metrics -------------------------------------------------
    def derived(self) -> Dict[str, Any]:
        """Metrics plus values the engine can compute from them."""
        m = dict(self.metrics)
        rev, margin = m.get("revenue_ltm"), m.get("ebitda_margin")
        if rev is not None and margin is not None and "ebitda" not in m:
            m["ebitda"] = rev * margin / 100.0
        cash, debt = m.get("cash"), m.get("total_debt")
        if cash is not None and debt is not None and "net_debt" not in m:
            m["net_debt"] = debt - cash
        ebitda, net_debt = m.get("ebitda"), m.get("net_debt")
        if ebitda and net_debt is not None and "net_debt_ebitda" not in m:
            m["net_debt_ebitda"] = net_debt / ebitda if ebitda > 0 else None
        return m

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanySnapshot":
        segs = [Segment(**s) for s in data.get("segments", []) or []]
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "segments"}
        return cls(segments=segs, **known)

    @classmethod
    def from_file(cls, path: Path) -> "CompanySnapshot":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


def text_blob(snapshot: CompanySnapshot) -> str:
    """Everything descriptive about the company, lower-cased, for keyword matching."""
    parts = [snapshot.sector, snapshot.industry, snapshot.description]
    parts += [s.name for s in snapshot.segments]
    return " ".join(p for p in parts if p).lower()


def primary_theme(theme_shares: Dict[str, float]) -> Optional[str]:
    mapped = {k: v for k, v in theme_shares.items() if k != "_unmapped" and v > 0}
    if not mapped:
        return None
    return max(mapped, key=mapped.get)
