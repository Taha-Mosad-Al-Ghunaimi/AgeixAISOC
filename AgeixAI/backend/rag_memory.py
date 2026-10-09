"""
AgeixAISOC — RAG Memory for SOC Context (ChromaDB).

Provides persistent short-term + long-term incident memory for the
LangGraph orchestrator agents.  Each decision package is embedded
and stored; agents can retrieve similar past incidents on demand.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("AgeixAI.rag_memory")

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    _chroma_available = True
except ImportError:
    logger.warning("chromadb not installed — RAG memory disabled")
    _chroma_available = False


MEMORY_COLLECTION_NAME = "soc_incident_memory"


class RagMemory:
    def __init__(self, persist_directory: str = "./data/rag_memory"):
        self._enabled = _chroma_available
        if not self._enabled:
            logger.warning("RagMemory running in NO-OP mode (chromadb missing)")
            self._collection = None
            return

        try:
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=MEMORY_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "RagMemory initialized (collection='%s', persist='%s', count=%d)",
                MEMORY_COLLECTION_NAME,
                persist_directory,
                self._collection.count(),
            )
        except Exception as exc:
            logger.error("RagMemory init failed: %s", exc)
            self._enabled = False
            self._collection = None

    def store_incident(self, decision: dict[str, Any]) -> str:
        if not self._enabled or self._collection is None:
            return ""

        doc_id = decision.get("decision_id") or str(uuid.uuid4())
        threat_name = decision.get("threat_name", "Unknown")
        mitre_id = decision.get("mitre_technique_id", "T0000")
        risk_score = decision.get("risk_score", 50)
        recommended_action = decision.get("recommended_action", "investigate")
        timestamp = decision.get("timestamp", datetime.now(timezone.utc).isoformat())

        document = json.dumps(decision, indent=2, default=str)
        metadata = {
            "threat_name": threat_name,
            "mitre_technique_id": mitre_id,
            "risk_score": risk_score,
            "recommended_action": recommended_action,
            "timestamp": timestamp,
        }

        try:
            self._collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[doc_id],
            )
            logger.info(
                "RAG incident stored: id=%s threat=%s risk=%d",
                doc_id, threat_name, risk_score,
            )
        except Exception as exc:
            logger.warning("RAG store failed: %s", exc)

        return doc_id

    def query_similar_incidents(
        self,
        threat_name: str = "",
        mitre_id: str = "",
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        if not self._enabled or self._collection is None:
            return []

        query_text = f"{threat_name} {mitre_id}".strip()
        if not query_text:
            query_text = "incident"

        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
        except Exception as exc:
            logger.warning("RAG query failed: %s", exc)
            return []

        incidents = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = (results["metadatas"][0][i] or {}) if results.get("metadatas") else {}
                try:
                    parsed = json.loads(doc)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"raw": doc}
                parsed["_meta"] = meta
                parsed["_distance"] = (
                    results["distances"][0][i] if results.get("distances") else None
                )
                incidents.append(parsed)

        logger.info("RAG query returned %d incidents for '%s'", len(incidents), query_text)
        return incidents

    def get_statistics(self) -> dict[str, Any]:
        if not self._enabled or self._collection is None:
            return {"enabled": False, "count": 0}
        try:
            count = self._collection.count()
            return {"enabled": True, "count": count, "collection": MEMORY_COLLECTION_NAME}
        except Exception as exc:
            return {"enabled": True, "count": 0, "error": str(exc)}


rag = RagMemory()
