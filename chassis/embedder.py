# embedder.py
# Phase 2 embedding-based matcher using fastembed (optional dependency).

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Component, MatchResult

if TYPE_CHECKING:
    # Only used for type hints; never causes an ImportError at runtime.
    from fastembed import TextEmbedding  # type: ignore

# Module-level cache so the model loads once per process.
_embedding_model: "TextEmbedding | None" = None


def _get_model() -> "TextEmbedding":
    global _embedding_model
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "fastembed is required for Phase 2 matching. "
                "Install it with: pip install chassis[embeddings]"
            ) from exc
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


def _cosine_similarity(a, b) -> float:
    """Return cosine similarity between two 1-D numpy arrays."""
    import numpy as np  # type: ignore

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def match_embeddings(
    prompt: str,
    components: list[Component],
    threshold: float = 0.5,
) -> list[MatchResult]:
    """Return MatchResult for every component whose description cosine-similarity
    to the prompt embedding is >= threshold.  Results are sorted descending by
    score; ties are broken alphabetically by component name.
    """
    if not components:
        return []

    model = _get_model()

    descriptions = [comp.description for comp in components]
    texts = [prompt] + descriptions

    # .embed() returns a generator; materialise it into a list of numpy arrays.
    embeddings = list(model.embed(texts))
    prompt_emb = embeddings[0]
    desc_embs = embeddings[1:]

    results: list[MatchResult] = []
    for comp, emb in zip(components, desc_embs):
        score = _cosine_similarity(prompt_emb, emb)
        if score >= threshold:
            results.append(
                MatchResult(
                    component=comp,
                    score=score,
                    requires_gate=False,
                    phase=2,
                )
            )

    results.sort(key=lambda r: (-r.score, r.component.name))
    return results
