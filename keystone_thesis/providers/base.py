from __future__ import annotations

from typing import List

from ..company import CompanySnapshot


class ProviderError(RuntimeError):
    pass


class DataProvider:
    """Interface every provider implements."""

    name = "base"

    def get(self, ticker: str) -> CompanySnapshot:  # pragma: no cover - interface
        raise NotImplementedError

    def available(self) -> List[str]:
        """Tickers this provider can list without a network call (may be empty)."""
        return []
