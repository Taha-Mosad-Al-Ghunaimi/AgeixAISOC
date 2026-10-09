"""
Local embedding model via Ollama (nomic-embed-text).
Used by ChromaDB to vectorize decision documents for semantic recall.
"""

import logging
from typing import List

logger = logging.getLogger("AgeixAI.rag.embeddings")

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMENSIONS = 768  # nomic-embed-text default


class OllamaEmbeddings:
    """
    LangChain-compatible embedding class that calls Ollama's embedding endpoint.
    Falls back to a zero-vector if Ollama is unreachable (pipeline never crashes).
    """

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._available: bool | None = None

    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        import httpx

        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            models = r.json().get("models", [])
            self._available = any(
                m["name"].startswith(self.model) for m in models
            )
            if not self._available:
                logger.warning(
                    "Embedding model '%s' not found in Ollama. "
                    "Pull it with: ollama pull %s",
                    self.model,
                    self.model,
                )
        except Exception as exc:
            logger.warning(
                "Ollama unreachable at %s: %s. Using zero-vector fallback.",
                self.base_url,
                exc,
            )
            self._available = False
        return self._available

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        if not self._check_available():
            return [0.0] * EMBEDDING_DIMENSIONS

        import httpx

        try:
            r = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30,
            )
            r.raise_for_status()
            embedding = r.json().get("embedding")
            if embedding and len(embedding) == EMBEDDING_DIMENSIONS:
                return embedding
            logger.warning(
                "Unexpected embedding dimension: got %d, expected %d",
                len(embedding or []),
                EMBEDDING_DIMENSIONS,
            )
        except Exception as exc:
            logger.warning("Ollama embedding failed: %s", exc)

        return [0.0] * EMBEDDING_DIMENSIONS


# Singleton
_embeddings: OllamaEmbeddings | None = None


def get_embeddings() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings()
    return _embeddings
