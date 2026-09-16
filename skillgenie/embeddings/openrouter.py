# ============================================================================
# Project      : SkillGenie
# File         : openrouter.py
# Description  : OpenRouter-hosted embedding provider.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from skillgenie.exceptions import EmbeddingError
from skillgenie.embeddings.base import EmbeddingProvider


class OpenRouterProvider(EmbeddingProvider):
    """
    Embedding provider backed by the OpenRouter API.

    Requires an API key configured under `openrouter.api_key`.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/text-embedding-3-small",
        **_: Any,
    ) -> None:
        """
        Initialize provider.

        Args:
            api_key: OpenRouter API key.
            base_url: OpenRouter base URL.
            model: Embedding model identifier.
        """

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

        if not self._api_key:
            raise EmbeddingError(
                "OpenRouter API key is not configured."
            )

    @property
    def dimensions(self) -> int:
        """
        Embedding dimensions (declared for the configured model).
        """

        model_dimensions = {
            "openai/text-embedding-3-small": 1536,
            "openai/text-embedding-3-large": 3072,
            "openai/text-embedding-ada-002": 1536,
        }

        return model_dimensions.get(self._model, 1536)

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

        payload = json.dumps(
            {
                "model": self._model,
                "input": [self.prepare(text) for text in texts],
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self._base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise EmbeddingError(
                f"OpenRouter embedding request failed "
                f"({exc.code}): {exc.read().decode('utf-8', 'ignore')}"
            ) from exc
        except urllib.error.URLError as exc:
            raise EmbeddingError(
                f"OpenRouter embedding request failed: {exc.reason}"
            ) from exc

        data = result.get("data", [])

        if len(data) != len(texts):
            raise EmbeddingError(
                "OpenRouter returned an unexpected number of embeddings."
            )

        return [entry.get("embedding", []) for entry in data]