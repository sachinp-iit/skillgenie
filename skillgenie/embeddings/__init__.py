# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : Embedding package exports.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.embeddings.base import EmbeddingProvider
from skillgenie.embeddings.factory import (
    get_embedding_provider,
    register_provider,
)
from skillgenie.embeddings.hash import HashEmbeddingProvider
from skillgenie.embeddings.local import LocalEmbeddingProvider
from skillgenie.embeddings.openrouter import OpenRouterProvider

__all__ = [
    "EmbeddingProvider",
    "get_embedding_provider",
    "register_provider",
    "LocalEmbeddingProvider",
    "OpenRouterProvider",
    "HashEmbeddingProvider",
]