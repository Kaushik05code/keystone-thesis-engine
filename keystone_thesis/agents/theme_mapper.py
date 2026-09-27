"""Theme-mapping agent: used only when keyword matching leaves most of a
company's revenue outside the thesis themes (e.g. vague segment names)."""

from __future__ import annotations

import json
from typing import Dict

from ..company import CompanySnapshot
from ..thesis import Thesis
from .llm import LLMClient

SYSTEM = (
    "You are an equity research analyst. Map a company's revenue to the themes of an "
    "investment thesis. Only use theme ids from the list you are given. Be conservative: "
    "if a business line does not clearly belong to a theme, leave it unmapped."
)


def map_themes_with_llm(snapshot: CompanySnapshot, thesis: Thesis, client: LLMClient) -> Dict[str, float]:
    themes = [{"id": t.id, "name": t.name, "keywords": t.keywords[:8]} for t in thesis.themes]
    user = json.dumps({
        "thesis": thesis.name,
        "themes": themes,
        "company": {
            "name": snapshot.name,
            "sector": snapshot.sector,
            "industry": snapshot.industry,
            "description": snapshot.description[:1500],
            "segments": [{"name": s.name, "revenue_share_pct": s.revenue_share_pct} for s in snapshot.segments],
        },
        "output": {"theme_shares": {"<theme_id>": "revenue share % (all shares sum to <= 100)"},
                   "reasoning": "one short paragraph"},
    }, indent=2)
    data = client.chat_json(SYSTEM, user, required=["theme_shares"])

    valid = {t.id for t in thesis.themes}
    shares = {k: float(v) for k, v in data["theme_shares"].items() if k in valid and float(v) > 0}
    total = sum(shares.values())
    if total > 100:
        shares = {k: v * 100 / total for k, v in shares.items()}
    shares["_unmapped"] = max(0.0, 100.0 - sum(shares.values()))
    return shares
