"""Live data from Yahoo Finance via ``yfinance``. No API key needed.

Install with ``pip install -e ".[live]"`` and use Yahoo tickers, for example
``HAL.NS`` (NSE) or ``500182.BO`` (BSE). Values are converted to crore.

Yahoo does not publish promoter pledging, customer concentration or export
share, so red flags that need them show up as "unchecked" in the report.
Add them by hand in a JSON snapshot if they matter to your thesis.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, Optional

from ..company import CompanySnapshot
from .base import DataProvider, ProviderError

CRORE = 1e7


def _num(x: Any) -> Optional[float]:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _row(frame, *names) -> list:
    """Values of the first matching row, newest first, NaNs dropped."""
    if frame is None or getattr(frame, "empty", True):
        return []
    for name in names:
        if name in frame.index:
            return [v for v in (_num(x) for x in frame.loc[name].tolist()) if v is not None]
    return []


class YahooProvider(DataProvider):
    name = "yahoo"

    def __init__(self, **_):
        try:
            import yfinance  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ProviderError('yfinance is not installed; run: pip install -e ".[live]"') from exc

    def get(self, ticker: str) -> CompanySnapshot:
        import yfinance as yf

        t = yf.Ticker(ticker)
        info = t.info or {}
        if not info.get("longName") and not info.get("shortName"):
            raise ProviderError(f"Yahoo Finance returned nothing for '{ticker}'")

        inc, bs, cf = t.income_stmt, t.balance_sheet, t.cashflow
        revenue_hist = _row(inc, "Total Revenue", "Operating Revenue")
        m: Dict[str, Optional[float]] = {}

        revenue = _num(info.get("totalRevenue")) or (revenue_hist[0] if revenue_hist else None)
        m["revenue_ltm"] = revenue / CRORE if revenue else None
        if len(revenue_hist) >= 4 and revenue_hist[3] > 0:
            m["revenue_cagr_3y"] = ((revenue_hist[0] / revenue_hist[3]) ** (1 / 3) - 1) * 100
        margin = _num(info.get("ebitdaMargins"))
        m["ebitda_margin"] = margin * 100 if margin is not None else None
        cash, debt = _num(info.get("totalCash")), _num(info.get("totalDebt"))
        m["cash"] = cash / CRORE if cash is not None else None
        m["total_debt"] = debt / CRORE if debt is not None else 0.0
        interest = _row(inc, "Interest Expense", "Interest Expense Non Operating")
        m["interest_expense"] = abs(interest[0]) / CRORE if interest else 0.0
        capex = _row(cf, "Capital Expenditure")
        m["capex"] = abs(capex[0]) / CRORE if capex else None
        current_debt = _row(bs, "Current Debt", "Current Debt And Capital Lease Obligation")
        m["debt_due_12m"] = current_debt[0] / CRORE if current_debt else None

        ebit, assets, cur_liab = _row(inc, "EBIT"), _row(bs, "Total Assets"), _row(bs, "Current Liabilities")
        if ebit and assets and cur_liab and assets[0] - cur_liab[0] > 0:
            m["roce"] = ebit[0] / (assets[0] - cur_liab[0]) * 100
        rnd = _row(inc, "Research And Development")
        if rnd and revenue:
            m["rnd_pct_revenue"] = rnd[0] / revenue * 100
        fcf = _row(cf, "Free Cash Flow")
        net_income = _row(inc, "Net Income", "Net Income Common Stockholders")
        if fcf and net_income and net_income[0] > 0:
            m["fcf_conversion_pct"] = fcf[0] / net_income[0] * 100

        pe = _num(info.get("trailingPE"))
        if pe is None and _num(info.get("trailingEps")) is not None and info["trailingEps"] < 0:
            pe = -1.0  # loss-making
        m["pe"] = pe
        insiders = _num(info.get("heldPercentInsiders"))
        m["promoter_holding_pct"] = insiders * 100 if insiders is not None else None

        return CompanySnapshot(
            ticker=ticker.upper(),
            name=info.get("longName") or info.get("shortName") or ticker,
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            description=info.get("longBusinessSummary", ""),
            exchange=info.get("exchange", ""),
            currency=info.get("currency", "INR"),
            units="crore",
            as_of=date.today().isoformat(),
            source="Yahoo Finance via yfinance",
            metrics={k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items() if v is not None},
        )
