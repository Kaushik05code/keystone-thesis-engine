import copy
from pathlib import Path

import pytest
import yaml

from keystone_thesis.thesis import ThesisError, load_thesis, parse_thesis

ROOT = Path(__file__).resolve().parent.parent
THESES = sorted((ROOT / "theses").glob("*.yaml"))


@pytest.mark.parametrize("path", THESES, ids=lambda p: p.stem)
def test_bundled_theses_are_valid(path):
    thesis = load_thesis(str(path))
    assert abs(sum(thesis.weights.values()) - 1.0) < 1e-6
    assert thesis.themes and thesis.traits and thesis.scenarios and thesis.bands


def _raw():
    with open(ROOT / "theses" / "india_structural_growth.yaml") as fh:
        return yaml.safe_load(fh)


def test_weights_must_sum_to_one():
    data = _raw()
    data["weights"]["theme_fit"] = 0.5
    with pytest.raises(ThesisError, match="sum to 1.0"):
        parse_thesis(data)


def test_missing_component_weight_is_rejected():
    data = _raw()
    del data["weights"]["valuation_tolerance"]
    with pytest.raises(ThesisError, match="missing components"):
        parse_thesis(data)


def test_macro_signal_must_reference_known_theme():
    data = _raw()
    data["macro"]["signals"][0]["themes"] = ["not_a_theme"]
    with pytest.raises(ThesisError, match="unknown themes"):
        parse_thesis(data)


def test_terminal_growth_below_cost_of_equity():
    data = _raw()
    data["valuation"]["terminal_growth_pct"] = 20
    with pytest.raises(ThesisError, match="terminal_growth_pct"):
        parse_thesis(data)


def test_short_name_resolves():
    assert load_thesis("quality_compounders").id == "quality_compounders"
