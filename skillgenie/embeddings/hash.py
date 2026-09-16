# ============================================================================
# Project      : SkillGenie
# File         : hash.py
# Description  : Deterministic, dependency-free embedding provider.
#
#                Produces stable fixed-size vectors from text hashes. Useful
#                for offline development, tests and environments without a
#                heavyweight model.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import hashlib
from typing import Any

from skillgenie.embeddings.base import EmbeddingProvider


class HashEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic hashing embedding provider.
    """

    def __init__(
        self,
        dimensions: int = 384,
        **_: Any,
    ) -> None:
        """
        Initialize provider.

        Args:
            dimensions: Number of embedding dimensions.
        """

        self._dimensions = int(dimensions)

    @property
    def dimensions(self) -> int:
        """
        Embedding dimensions.
        """

        return self._dimensions

    def _embed_token(self, token: str) -> list[float]:
        """
        Embed a single n-gram token.
        """

        digest = hashlib.sha256(token.encode("utf-8")).digest()

        vector = [0.0] * self._dimensions

        for index, byte in enumerate(digest):
            position = index % self._dimensions
            vector[position] += (byte / 255.0) * 2.0 - 1.0

        return vector

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text.
        """

        embeddings = self.embed_texts([text])

        return embeddings[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts.
        """

        vectors: list[list[float]] = []

        for text in texts:
            normalized = self.prepare(text).lower()

            if not normalized:
                vectors.append([0.0] * self._dimensions)
                continue

            tokens = normalized.split()

            vector = [0.0] * self._dimensions

            for token in tokens:
                token_vector = self._embed_token(token)
                for index, value in enumerate(token_vector):
                    vector[index] += value

            norm = sum(value * value for value in vector) ** 0.5

            if norm > 0:
                vector = [value / norm for value in vector]

            vectors.append(vector)

        return vectors