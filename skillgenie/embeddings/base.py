# ============================================================================
# Project      : SkillGenie
# File         : base.py
# Description  : Abstract embedding provider contract.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from abc import ABC, abstractmethod
from typing import Any


class EmbeddingProvider(ABC):
    """
    Base contract for embedding providers.

    Implementations translate text into dense vector representations used for
    similarity search and duplicate detection.
    """

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        Number of dimensions of the produced embeddings.
        """

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text.
        """

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts.
        """

    def prepare(self, text: str) -> str:
        """
        Normalize text before embedding.
        """

        return " ".join(text.split()) if text else ""