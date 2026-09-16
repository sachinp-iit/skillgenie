"""
Tests for the embedding providers and factory.
"""

import pytest

from skillgenie.embeddings.base import EmbeddingProvider
from skillgenie.embeddings.factory import get_embedding_provider
from skillgenie.embeddings.hash import HashEmbeddingProvider


def test_hash_provider_dimensions():
    provider = HashEmbeddingProvider(dimensions=384)

    assert provider.dimensions == 384


def test_hash_embedding_deterministic():
    provider = HashEmbeddingProvider(dimensions=64)

    text = "search the web and summarize results"

    first = provider.embed_text(text)
    second = provider.embed_text(text)

    assert len(first) == 64
    assert first == second


def test_hash_embedding_differs_for_different_text():
    provider = HashEmbeddingProvider(dimensions=64)

    a = provider.embed_text("summarize a document")
    b = provider.embed_text("book a flight")

    assert a != b


def test_hash_embed_texts_batch():
    provider = HashEmbeddingProvider(dimensions=32)

    embeddings = provider.embed_texts(["one", "two", "three"])

    assert len(embeddings) == 3
    assert all(len(embedding) == 32 for embedding in embeddings)


def test_embedding_provider_contract():
    assert issubclass(HashEmbeddingProvider, EmbeddingProvider)

    assert isinstance(
        HashEmbeddingProvider(dimensions=16),
        EmbeddingProvider,
    )


def test_factory_hash_provider(monkeypatch, tmp_path):
    from skillgenie.config import Config

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "hash")

    config = Config(str(tmp_path / "config.json"))

    provider = get_embedding_provider(config)

    assert isinstance(provider, HashEmbeddingProvider)


def test_factory_unknown_provider_raises(monkeypatch, tmp_path):
    from skillgenie.config import Config
    from skillgenie.exceptions import SkillGenieError

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "nonexistent")

    config = Config(str(tmp_path / "config.json"))

    with pytest.raises(SkillGenieError):
        get_embedding_provider(config)