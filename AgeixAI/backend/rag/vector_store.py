"""
Vector store backed by ChromaDB with local embeddings via Ollama (nomic-embed-text).

Collection: "human_decisions_memory" stores learned human decisions for semantic recall.

Keeps the same interface as the original mock store (search, insert, count, list_knowledge_bases)
so existing code in agents.py, adaptive_rag.py, and main.py continues to work unchanged.
"""

import json
import logging
import os
import random
import tempfile
from typing import Any

from rag.embeddings import get_embeddings
from rag.knowledge_bases import (
    KNOWLEDGE_BASE_METADATA,
    KnowledgeBaseName,
    get_kb_names,
)

logger = logging.getLogger("AgeixAI.rag.vector_store")

CHROMA_PERSIST_DIR = os.path.join(
    tempfile.gettempdir(), "ageixai_chroma", "human_decisions_memory"
)
CHROMA_COLLECTION_NAME = "human_decisions_memory"


class VectorStore:
    def __init__(self, provider: str = "chroma") -> None:
        self.provider = provider
        self._collection: Any | None = None
        self._chroma_client: Any | None = None
        self._initialized = False
        logger.info("VectorStore initialized (provider=%s)", provider)

    # ── ChromaDB lazy init ───────────────────────────────────────────────────

    def _ensure_client(self) -> None:
        if self._initialized:
            return
        try:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(os.path.dirname(CHROMA_PERSIST_DIR), exist_ok=True)

            self._chroma_client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(
                "ChromaDB connected: collection='%s' persist='%s'",
                CHROMA_COLLECTION_NAME,
                CHROMA_PERSIST_DIR,
            )
        except Exception as exc:
            logger.warning(
                "ChromaDB unavailable (%s) — falling back to mock store. "
                "Install with: pip install chromadb",
                exc,
            )
            # Fall back gracefully — store in memory dict
            self.provider = "mock"

    # ── Embedding ────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        try:
            emb = get_embeddings()
            return emb.embed_query(text)
        except Exception as exc:
            logger.warning("Embedding call failed: %s", exc)
            return [0.0] * 768

    # ── Public interface ─────────────────────────────────────────────────────

    def search(
        self,
        knowledge_base: KnowledgeBaseName,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar documents. Supports all KB names."""
        # Only learned_decisions uses ChromaDB; others fall back to mock
        if knowledge_base != "learned_decisions":
            return self._mock_search(knowledge_base, query, top_k)

        self._ensure_client()
        if self.provider == "mock":
            return self._mock_search(knowledge_base, query, top_k)

        try:
            query_embedding = self._embed(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 50),
                include=["documents", "metadatas", "distances"],
            )

            documents = results.get("documents", [[]])[0] or []
            metadatas = results.get("metadatas", [[]])[0] or []
            distances = results.get("distances", [[]])[0] or []

            out = []
            for i in range(len(documents)):
                meta = metadatas[i] if i < len(metadatas) else {}
                dist = distances[i] if i < len(distances) else 0.0
                # Convert L2 distance to a 0-1 similarity score
                score = max(0.0, 1.0 - dist / 2.0)
                out.append(
                    {
                        "id": meta.get("doc_id", f"chroma-{i}"),
                        "content": documents[i],
                        "metadata": meta,
                        "score": round(score, 4),
                    }
                )

            return out
        except Exception as exc:
            logger.warning("ChromaDB search failed: %s — falling back to mock", exc)
            return self._mock_search(knowledge_base, query, top_k)

    def insert(
        self,
        knowledge_base: KnowledgeBaseName,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert a document. Only learned_decisions persists to ChromaDB."""
        if knowledge_base != "learned_decisions":
            return self._mock_insert(knowledge_base, doc_id, content, metadata)

        self._ensure_client()
        if self.provider == "mock":
            return self._mock_insert(knowledge_base, doc_id, content, metadata)

        meta = metadata or {}
        meta["doc_id"] = doc_id

        try:
            embedding = self._embed(content)
            self._collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta],
                embeddings=[embedding],
            )
            logger.info(
                "ChromaDB insert: %s/%s (%s docs)",
                knowledge_base,
                doc_id,
                self._collection.count(),
            )
        except Exception as exc:
            logger.warning(
                "ChromaDB insert failed (%s) — falling back to mock", exc
            )
            return self._mock_insert(knowledge_base, doc_id, content, metadata)

        if knowledge_base in KNOWLEDGE_BASE_METADATA:
            KNOWLEDGE_BASE_METADATA[knowledge_base]["document_count"] = (
                self.count(knowledge_base)
            )

        return {"id": doc_id, "content": content, "metadata": meta}

    def count(self, knowledge_base: KnowledgeBaseName) -> int:
        """Return document count. For learned_decisions uses ChromaDB."""
        if knowledge_base != "learned_decisions":
            return len(_MOCK_DOCUMENTS.get(knowledge_base, []))

        self._ensure_client()
        if self.provider == "mock":
            return len(_MOCK_DOCUMENTS.get(knowledge_base, []))

        try:
            return self._collection.count()
        except Exception:
            return len(_MOCK_DOCUMENTS.get(knowledge_base, []))

    def list_knowledge_bases(self) -> list[dict[str, Any]]:
        return [
            {"name": kb, **KNOWLEDGE_BASE_METADATA.get(kb, {})}
            for kb in get_kb_names()
        ]

    def get_all_memories(
        self,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve all learned memories (for /api/brain-memory).
        Supports optional text query for semantic search.
        """
        self._ensure_client()

        if self.provider == "mock":
            docs = _MOCK_DOCUMENTS.get("learned_decisions", [])
            if query:
                docs = [
                    d
                    for d in docs
                    if query.lower() in d.get("content", "").lower()
                ]
            total = len(docs)
            page = docs[offset : offset + limit]
            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "memories": [
                    {
                        "id": d["id"],
                        "content": d["content"],
                        "metadata": d.get("metadata", {}),
                        "score": 1.0,
                    }
                    for d in page
                ],
            }

        try:
            if query:
                query_embedding = self._embed(query)
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"],
                )
            else:
                results = self._collection.get(
                    limit=limit,
                    offset=offset,
                    include=["documents", "metadatas"],
                )

            ids = results.get("ids", [])
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            distances = results.get("distances")

            memories = []
            for i in range(len(ids)):
                dist = distances[0][i] if distances and distances[0] else 0.0
                score = max(0.0, 1.0 - dist / 2.0) if distances else 1.0
                memories.append(
                    {
                        "id": ids[i],
                        "content": documents[i] if i < len(documents) else "",
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "score": round(score, 4),
                    }
                )

            total = self._collection.count()

            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "memories": memories[:limit],
            }
        except Exception as exc:
            logger.warning("ChromaDB get_all failed: %s", exc)
            return {"total": 0, "offset": 0, "limit": limit, "memories": []}

    def delete_memory(self, doc_id: str) -> bool:
        """Delete a memory by doc_id."""
        self._ensure_client()
        if self.provider == "mock":
            docs = _MOCK_DOCUMENTS.get("learned_decisions", [])
            _MOCK_DOCUMENTS["learned_decisions"] = [
                d for d in docs if d["id"] != doc_id
            ]
            return True
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except Exception as exc:
            logger.warning("ChromaDB delete failed: %s", exc)
            return False

    # ── Mock fallback helpers (same as original implementation) ──────────────

    def _mock_search(
        self,
        knowledge_base: KnowledgeBaseName,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        docs = _MOCK_DOCUMENTS.get(knowledge_base, [])
        scored = []
        for doc in docs:
            score = self._mock_score(query, doc["content"])
            scored.append({**doc, "score": round(score, 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _mock_score(query: str, content: str) -> float:
        query_tokens = set(query.lower().split())
        content_tokens = set(content.lower().split())
        intersection = query_tokens & content_tokens
        if not intersection:
            return random.uniform(0.1, 0.4)
        return min(1.0, len(intersection) / max(len(query_tokens), 1) * 0.8 + 0.2)

    def _mock_insert(
        self,
        knowledge_base: KnowledgeBaseName,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if knowledge_base not in _MOCK_DOCUMENTS:
            _MOCK_DOCUMENTS[knowledge_base] = []
        doc = {"id": doc_id, "content": content, "metadata": metadata or {}}
        _MOCK_DOCUMENTS[knowledge_base].append(doc)
        if knowledge_base in KNOWLEDGE_BASE_METADATA:
            KNOWLEDGE_BASE_METADATA[knowledge_base]["document_count"] = len(
                _MOCK_DOCUMENTS[knowledge_base]
            )
        return doc


# ── Mock fallback documents (preserved from original) ────────────────────────

_MOCK_DOCUMENTS: dict[KnowledgeBaseName, list[dict[str, Any]]] = {
    "past_incidents": [
        {"id": "inc-001", "content": "Ransomware attack ...", "metadata": {}},
        {"id": "inc-002", "content": "Log4j exploitation ...", "metadata": {}},
        {"id": "inc-003", "content": "Phishing campaign ...", "metadata": {}},
    ],
    "threat_intel": [
        {"id": "ti-001", "content": "APT29 — DNS tunneling ...", "metadata": {}},
        {"id": "ti-002", "content": "BlackCat — RaaS ...", "metadata": {}},
        {"id": "ti-003", "content": "FIN7 — web exploitation ...", "metadata": {}},
    ],
    "sigma_rules": [
        {"id": "sig-001", "content": "title: Suspicious LSASS Access ...", "metadata": {}},
        {"id": "sig-002", "content": "title: PowerShell Encoded Command ...", "metadata": {}},
        {"id": "sig-003", "content": "title: Remote Desktop from Unknown IP ...", "metadata": {}},
    ],
    "iso_27001": [
        {"id": "iso-001", "content": "A.12.6.1 — Management ...", "metadata": {}},
        {"id": "iso-002", "content": "A.16.1.5 — Response ...", "metadata": {}},
        {"id": "iso-003", "content": "NIST CSF DE.CM — Monitoring ...", "metadata": {}},
    ],
    "cve_kev": [
        {"id": "cve-001", "content": "CVE-2025-44228 — Log4j ...", "metadata": {}},
        {"id": "cve-002", "content": "CVE-2024-6387 — OpenSSH ...", "metadata": {}},
        {"id": "cve-003", "content": "CVE-2023-23397 — Outlook ...", "metadata": {}},
    ],
    "cmdb": [
        {"id": "cmdb-001", "content": "web-01: Ubuntu 22.04 ...", "metadata": {}},
        {"id": "cmdb-002", "content": "dc-01: Windows Server 2025 ...", "metadata": {}},
        {"id": "cmdb-003", "content": "ws-01: Windows 11 ...", "metadata": {}},
    ],
    "historical_logs": [
        {"id": "log-001", "content": "2026-06-15T03:22:00Z ...", "metadata": {}},
        {"id": "log-002", "content": "2026-06-20T14:10:00Z ...", "metadata": {}},
        {"id": "log-003", "content": "2026-07-01T08:45:00Z ...", "metadata": {}},
    ],
    "learned_decisions": [],
    "external_threat_intel": [],
    "soc_academy": [],
}


# ── Singleton ────────────────────────────────────────────────────────────────

_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
