import json

from keystone_thesis.cli import main


def test_list(capsys):
    assert main(["list"]) == 0
    assert "india_structural_growth" in capsys.readouterr().out


def test_score_summary(capsys):
    assert main(["score", "ARYADEF", "-t", "india_structural_growth"]) == 0
    assert "Overall" in capsys.readouterr().out


def test_score_json(capsys):
    assert main(["score", "KAVERISOFT", "-t", "quality_compounders", "-f", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["thesis"]["id"] == "quality_compounders"


def test_score_writes_all_formats(tmp_path):
    assert main(["score", "METROFASH", "-t", "india_structural_growth", "-o", str(tmp_path)]) == 0
    assert {p.suffix for p in tmp_path.iterdir()} == {".md", ".html", ".json"}


def test_rank_and_compare(capsys):
    assert main(["rank", "-t", "india_structural_growth"]) == 0
    assert main(["compare", "BHARATLINK"]) == 0
    out = capsys.readouterr().out
    assert "Leaderboard" in out and "under different theses" in out


def test_unknown_ticker_is_a_clean_error(capsys):
    assert main(["score", "NOPE", "-t", "india_structural_growth"]) == 2
    assert "no snapshot" in capsys.readouterr().err
