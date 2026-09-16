# ============================================================================
# Project      : SkillGenie
# File         : factory.py
# Description  : Embedding provider factory.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.embeddings.base import EmbeddingProvider
from skillgenie.embeddings.hash import HashEmbeddingProvider
from skillgenie.embeddings.local import LocalEmbeddingProvider
from skillgenie.embeddings.openrouter import OpenRouterProvider
from skillgenie.exceptions import EmbeddingError, ConfigurationError

# Provider registry for extension
PROVIDERS: dict[str, type[EmbeddingProvider]] = {
    "sentence-transformers": LocalEmbeddingProvider,
    "local": LocalEmbeddingProvider,
    "openrouter": OpenRouterProvider,
    "hash": HashEmbeddingProvider,
    "deterministic": HashEmbeddingProvider,
}


def register_provider(
    name: str,
    provider_class: type[EmbeddingProvider],
) -> None:
    """
    Register a custom embedding provider.
    """

    PROVIDERS[name] = provider_class


def get_embedding_provider(
    config: Config,
    provider: str | None = None,
    **overrides: Any,
) -> EmbeddingProvider:
    """
    Build an embedding provider from configuration.

    Args:
        config: SkillGenie configuration.
        provider: Provider name. Defaults to `embeddings.provider`.
        **overrides: Constructor overrides (e.g. model name).

    Returns:
        Configured embedding provider.
    """

    provider_name = (
        provider
        or config.get("embeddings.provider", "sentence-transformers")
    )

    provider_cls = PROVIDERS.get(provider_name)

    if provider_cls is None:
        raise ConfigurationError(
            f"Unsupported embedding provider: {provider_name}"
        )

    if provider_cls is LocalEmbeddingProvider:
        return provider_cls(
            model_name=overrides.get(
                "model",
                config.get("embeddings.model", "BAAI/bge-small-en-v1.5"),
            ),
            batch_size=overrides.get(
                "batch_size",
                config.get_int("embeddings.batch_size", 32),
            ),
        )

    if provider_cls is OpenRouterProvider:
        return provider_cls(
            api_key=overrides.get(
                "api_key",
                config.get("openrouter.api_key", ""),
            ),
            base_url=overrides.get(
                "base_url",
                config.get("openrouter.base_url", "https://openrouter.ai/api/v1"),
            ),
            model=overrides.get(
                "model",
                config.get("openrouter.embedding_model", ""),
            ),
        )

    if provider_cls is HashEmbeddingProvider:
        return provider_cls(
            dimensions=overrides.get(
                "dimensions",
                config.get_int("embeddings.dimensions", 384),
            ),
        )

    raise EmbeddingError(f"Unhandled provider: {provider_name}")