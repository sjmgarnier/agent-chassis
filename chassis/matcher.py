from .models import Component, MatchResult


def match_keywords(prompt: str, components: list) -> list:
    prompt_lower = prompt.lower()
    results = []

    for comp in components:
        score = 0
        for kw in comp.keywords:
            if kw.lower() in prompt_lower:
                score += 1
        for topic in comp.topics:
            if topic.lower() in prompt_lower:
                score += 1
        if score > 0:
            results.append(MatchResult(
                component=comp,
                score=float(score),
                requires_gate=False,
                phase=1,
            ))

    results.sort(key=lambda r: (-r.score, r.component.name))
    return results
