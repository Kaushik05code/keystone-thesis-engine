"""Keystone Thesis Engine: write your investment thesis in YAML, score any company against it."""

from .company import CompanySnapshot, Segment
from .scoring import ScoreCard, score_company
from .thesis import Thesis, ThesisError, load_thesis

__version__ = "2.0.0"

__all__ = [
    "CompanySnapshot",
    "Segment",
    "ScoreCard",
    "score_company",
    "Thesis",
    "ThesisError",
    "load_thesis",
    "__version__",
]
