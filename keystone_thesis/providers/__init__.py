"""Data providers turn a ticker into a :class:`CompanySnapshot`.

Add your own by subclassing :class:`DataProvider` and registering it in
``PROVIDERS`` (for example a Screener.in export, a broker API, or a CSV).
"""

from __future__ import annotations

from .base import DataProvider, ProviderError
from .sample import SampleProvider

PROVIDERS = {"sample": SampleProvider}


def get_provider(name: str, **kwargs) -> DataProvider:
    if name == "yahoo":
        from .yahoo import YahooProvider  # optional dependency, imported lazily

        return YahooProvider(**kwargs)
    if name not in PROVIDERS:
        raise ProviderError(f"unknown provider '{name}' (choose from: sample, yahoo)")
    return PROVIDERS[name](**kwargs)


__all__ = ["DataProvider", "ProviderError", "SampleProvider", "get_provider"]
