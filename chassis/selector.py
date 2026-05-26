import logging
from pathlib import Path
from typing import Optional

from .config import load_config
from .loader import load_components
from .matcher import match_keywords
from .models import MatchResult

logger = logging.getLogger(__name__)


def select(prompt: str, project_root: Optional[Path] = None) -> list:
    config = load_config(project_root)
    components = load_components(project_root)

    if config.selector_phase == 2:
        try:
            from .embedder import match_embeddings
            results = match_embeddings(prompt, components, config.threshold)
        except ImportError:
            logger.warning("fastembed not available; falling back to keyword matching")
            results = match_keywords(prompt, components)
    else:
        results = match_keywords(prompt, components)

    for result in results:
        if config.gate_enabled:
            result.requires_gate = True
        else:
            result.requires_gate = result.component.gate

    return results
