from dataclasses import dataclass, field


@dataclass
class Component:
    name: str
    description: str
    body: str
    gate: bool = False
    keywords: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    source: str = "global"


@dataclass
class MatchResult:
    component: Component
    score: float
    requires_gate: bool
    phase: int


@dataclass
class Config:
    selector_phase: int = 1
    threshold: float = 0.5
    gate_enabled: bool = False
    notify_enabled: bool = True
