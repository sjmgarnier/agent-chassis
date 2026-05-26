from chassis.models import Component, MatchResult, Config


def test_component_defaults():
    comp = Component(name="git", description="Git stuff", body="# Git")
    assert comp.gate is False
    assert comp.keywords == []
    assert comp.topics == []
    assert comp.source == "global"


def test_match_result_fields():
    comp = Component(name="git", description="", body="")
    result = MatchResult(component=comp, score=2.0, requires_gate=False, phase=1)
    assert result.phase == 1


def test_config_defaults():
    config = Config()
    assert config.selector_phase == 1
    assert config.threshold == 0.5
    assert config.gate_enabled is False
    assert config.notify_enabled is True
