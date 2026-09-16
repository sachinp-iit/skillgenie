# ============================================================================
# Project      : SkillGenie
# File         : local.py
# Description  : Sentence-transformers embedding provider.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.exceptions import EmbeddingError
from skillgenie.embeddings.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider backed by sentence-transformers models.

    The underlying model is loaded lazily on first use.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 32,
        **_: Any,
    ) -> None:
        """
        Initialize provider.

        Args:
            model_name: Sentence-transformers model identifier.
            batch_size: Batch size for embedding computation.
        """

        self._model_name = model_name
        self._batch_size = batch_size
        self._model = None

    def _load_model(self) -> Any:
        """
        Lazily load the sentence-transformers model.
        """

        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is not installed."
            ) from exc

        try:
            self._model = SentenceTransformer(self._model_name)
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to load embedding model '{self._model_name}': {exc}"
            ) from exc

        return self._model

    @property
    def dimensions(self) -> int:
        """
        Embedding dimensions for the configured model.
        """

        model = self._load_model()

        method = getattr(
            model,
            "get_embedding_dimension",
            getattr(model, "get_sentence_embedding_dimension", None),
        )

        return int(method()) if method else 384

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

        model = self._load_model()

        processed = [self.prepare(text) for text in texts]

        try:
            vectors = model.encode(
                processed,
                batch_size=self._batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding generation failed: {exc}"
            ) from exc

        return [list(map(float, vector)) for vector in vectors]