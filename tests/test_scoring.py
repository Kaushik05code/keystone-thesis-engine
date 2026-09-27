import pytest

from keystone_thesis import CompanySnapshot, load_thesis, score_company
from keystone_thesis.providers import get_provider
from keystone_thesis.scoring.components import implied_growth, map_themes
from keystone_thesis.thesis import COMPONENTS

INDIA = load_thesis("india_structural_growth")
QUALITY = load_thesis("quality_compounders")
SAMPLE = get_provider("sample")


def card(ticker, thesis=INDIA):
    return score_company(SAMPLE.get(ticker), thesis)


def test_every_sample_scores_between_0_and_100():
    for thesis in (INDIA, QUALITY):
        for t in SAMPLE.available():
            c = card(t, thesis)
            assert 0 <= c.overall <= 100
            for k in COMPONENTS:
                assert 0 <= c.components[k].score <= 100


def test_overall_is_weighted_sum_when_no_gate_fails():
    c = card("ARYADEF")
    assert not c.gate_capped
    expected = sum(c.components[k].score * INDIA.weights[k] for k in COMPONENTS)
    assert c.overall == pytest.approx(expected)


def test_scoring_is_deterministic():
    assert card("BHARATLINK").overall == card("BHARATLINK").overall


def test_failed_gate_caps_the_score():
    c = card("JALNIDHI")  # promoter pledge 34% breaks the <25% gate
    assert c.gate_capped
    assert c.overall <= INDIA.gate_cap
    assert any(g["status"] == "fail" for g in c.gates)


def test_the_thesis_changes_the_answer():
    # A value retailer is outside the India infrastructure themes but is a quality business.
    india, quality = card("METROFASH", INDIA), card("METROFASH", QUALITY)
    assert india.components["theme_fit"].score < quality.components["theme_fit"].score
    assert india.overall != quality.overall


def test_theme_mapping_uses_revenue_segments():
    shares = map_themes(SAMPLE.get("BHARATLINK"), INDIA)
    assert shares["logistics"] == pytest.approx(90.0)  # rail freight + warehousing
    assert shares["_unmapped"] == pytest.approx(10.0)  # last-mile delivery


def test_analyst_theme_override_wins():
    snap = SAMPLE.get("KAVERISOFT")
    snap.themes = {"digital_infra": 100}
    assert score_company(snap, INDIA).components["theme_fit"].score == pytest.approx(80.0)


def test_loss_maker_gets_loss_making_valuation_score():
    c = card("NAVYASEMI")
    assert c.components["valuation_tolerance"].score == INDIA.loss_making_score


def test_reverse_dcf_is_monotonic_in_pe():
    growths = [implied_growth(pe, 0.125, 10, 0.05) for pe in (8, 15, 25, 40, 60)]
    assert growths == sorted(growths)
    assert implied_growth(10, 0.125, 10, 0.05) == pytest.approx(0.0, abs=0.01)


def test_heavily_indebted_company_fails_resilience():
    c = card("SURYAGRID")
    assert c.components["financial_resilience"].score < 20


def test_missing_data_is_flagged_not_rewarded():
    snap = CompanySnapshot(ticker="EMPTY", name="Empty Co", description="solar parks",
                           metrics={"pe": 20})
    c = score_company(snap, INDIA)
    assert c.data_coverage < 0.6
    assert c.components["financial_resilience"].score == 40.0
    assert c.components["execution_risk"].score <= INDIA.execution_unknown_cap


def test_sensitivity_moves_in_the_right_direction():
    c = card("ARYADEF")
    for k in COMPONENTS:
        row = c.sensitivity[k]
        assert row["-20"] <= row["-10"] <= row["+10"] <= row["+20"]


def test_falling_inflation_counts_as_a_tailwind():
    cpi = next(r for r in card("ARYADEF").components["macro_alignment"].inputs["signals"]
               if r["signal"].startswith("CPI"))
    assert cpi["trend"] == "down" and cpi["credit"] == 1.0
