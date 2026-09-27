"""Reads company snapshots from JSON files, one file per ticker.

The bundled ``data/sample`` folder holds FICTIONAL companies so the engine
runs offline with zero API keys. Point ``data_dir`` at your own folder to
score real companies from data you collected yourself.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..company import CompanySnapshot
from .base import DataProvider, ProviderError

_REPO_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"


class SampleProvider(DataProvider):
    name = "sample"

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        elif (Path.cwd() / "data" / "sample").exists():
            self.data_dir = Path.cwd() / "data" / "sample"
        else:
            self.data_dir = _REPO_SAMPLE
        if not self.data_dir.exists():
            raise ProviderError(f"data folder not found: {self.data_dir}")

    def available(self) -> List[str]:
        return sorted(p.stem for p in self.data_dir.glob("*.json"))

    def get(self, ticker: str) -> CompanySnapshot:
        path = self.data_dir / f"{ticker.upper()}.json"
        if not path.exists():
            raise ProviderError(
                f"no snapshot for '{ticker}' in {self.data_dir} "
                f"(available: {', '.join(self.available()) or 'none'})"
            )
        snap = CompanySnapshot.from_file(path)
        snap.source = snap.source or f"file:{path.name}"
        return snap
