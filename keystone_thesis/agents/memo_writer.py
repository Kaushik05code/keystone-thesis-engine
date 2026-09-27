"""Memo agent: turns a finished score card into a short investment memo.

It is given the scores and every input behind them, and is told not to
invent numbers. The score itself is never changed by the LLM.
"""

from __future__ import annotations

import json

from ..scoring import ScoreCard
from ..thesis import Thesis
from .llm import LLMClient

SYSTEM = (
    "You are a buy-side analyst writing a one-page memo for an investment committee. "
    "Use ONLY the numbers in the score card; never invent data. Plain English, no hype. "
    "Structure: 1) Verdict in two sentences. 2) Why it fits or does not fit the thesis. "
    "3) Top three positives with the data behind each. 4) Top three red flags with the data. "
    "5) What would have to change for the score to move 10+ points (use the sensitivity table). "
    "6) Data gaps an analyst should close before acting. Markdown, under 450 words."
)


def write_memo(card: ScoreCard, thesis: Thesis, client: LLMClient) -> str:
    payload = {
        "thesis": {"name": thesis.name, "summary": thesis.summary, "horizon_years": thesis.horizon_years},
        "score_card": card.to_dict(),
        "company_description": card.snapshot.description[:1500],
    }
    payload["score_card"].pop("memo", None)
    return client.chat(SYSTEM, json.dumps(payload, indent=2, default=str), max_tokens=1200).strip()
