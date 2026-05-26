# embedder.py
# Phase 2 embedding-based matcher using fastembed (optional dependency).

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from .models import Component, MatchResult

if TYPE_CHECKING:
    # Only used for type hints; never causes an ImportError at runtime.
    from fastembed import TextEmbedding  # type: ignore

try:
    import numpy as np  # type: ignore
except ImportError:
    np = None  # type: ignore[assignment]

# Module-level cache so the model loads once per process.
_embedding_model: "TextEmbedding | None" = None
_model_lock = threading.Lock()


def _get_model() -> "TextEmbedding":
    global _embedding_model
    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:  # double-checked locking
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
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
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
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")
    if not components:
        return []

    model = _get_model()

    descriptions = [comp.description for comp in components]
    texts = [prompt] + descriptions

    # embed() is a lazy generator; materialise into a list so we can index by position
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

    # Sort descending by score; ties broken alphabetically by name
    results.sort(key=lambda r: (-r.score, r.component.name))
    return results
