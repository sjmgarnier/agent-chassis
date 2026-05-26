import pytest
from chassis.models import Component
from chassis.embedder import match_embeddings


def make_comp(name, description):
    return Component(name=name, description=description, body="", keywords=[], topics=[])


@pytest.mark.slow
def test_match_above_threshold_returns_result():
    """Semantically similar prompt and description should produce a match."""
    comp = make_comp("git", "Git workflow and commit conventions")
    results = match_embeddings("git commit my changes", [comp])
    assert len(results) >= 1
    assert results[0].score >= 0.5
    assert results[0].phase == 2


@pytest.mark.slow
def test_match_below_threshold_returns_empty():
    """Unrelated prompt vs description with a high threshold should return no matches."""
    comp = make_comp("cooking", "Recipes for French cuisine and baking techniques")
    results = match_embeddings("git commit my changes", [comp], threshold=0.9)
    assert results == []


@pytest.mark.slow
def test_result_fields():
    """Returned MatchResult must have correct field values."""
    comp = make_comp("git", "Git workflow and commit conventions")
    results = match_embeddings("git commit my changes", [comp])
    assert len(results) >= 1
    r = results[0]
    assert r.requires_gate is False
    assert r.phase == 2
    assert isinstance(r.score, float)
    assert 0.0 <= r.score <= 1.0


@pytest.mark.slow
def test_sorted_by_score_descending():
    """Results must be sorted descending by score; ties broken alphabetically."""
    comp_git = make_comp("git", "Git version control, commits, branches, and merging")
    comp_cooking = make_comp("cooking", "Recipes for French cuisine and baking techniques")
    results = match_embeddings("git commit to a branch", [comp_git, comp_cooking], threshold=0.0)
    # Both components should come back (threshold=0.0 allows everything)
    assert len(results) == 2
    # git description should score higher than cooking description for this prompt
    assert results[0].score >= results[1].score
    assert results[0].component.name == "git"
