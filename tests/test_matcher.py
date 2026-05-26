import pytest
from chassis.models import Component
from chassis.matcher import match_keywords


def make_comp(name, keywords=None, topics=None):
    return Component(name=name, description="", body="", keywords=keywords or [], topics=topics or [])


def test_matches_exact_keyword():
    comp = make_comp("git", keywords=["commit"])
    results = match_keywords("I need to commit my changes", [comp])
    assert len(results) == 1
    assert results[0].component.name == "git"
    assert results[0].phase == 1


def test_matches_keyword_as_substring():
    comp = make_comp("git", keywords=["commit"])
    results = match_keywords("reviewing commits today", [comp])
    assert len(results) == 1


def test_case_insensitive():
    comp = make_comp("git", keywords=["Git", "Commit"])
    results = match_keywords("GIT COMMIT", [comp])
    assert len(results) == 1
    assert results[0].score == 2.0


def test_no_match_returns_empty():
    comp = make_comp("r-pkg", keywords=["devtools", "roxygen"])
    results = match_keywords("fix the login bug", [comp])
    assert results == []


def test_ranked_by_score():
    comp_a = make_comp("a", keywords=["git", "commit", "branch"])
    comp_b = make_comp("b", keywords=["git"])
    results = match_keywords("git commit to branch", [comp_a, comp_b])
    assert results[0].component.name == "a"
    assert results[1].component.name == "b"


def test_ties_broken_alphabetically():
    comp_a = make_comp("alpha", keywords=["git"])
    comp_b = make_comp("beta", keywords=["git"])
    results = match_keywords("git stuff", [comp_a, comp_b])
    assert results[0].component.name == "alpha"


def test_topic_match_counts():
    comp = make_comp("git", keywords=["git"], topics=["version_control"])
    results = match_keywords("version_control workflow", [comp])
    assert results[0].score == 1.0


def test_requires_gate_defaults_false():
    comp = make_comp("git", keywords=["git"])
    results = match_keywords("git stuff", [comp])
    assert results[0].requires_gate is False
