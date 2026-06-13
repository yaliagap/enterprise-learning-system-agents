"""Mock Foundry IQ provider: seeds an ephemeral ChromaDB collection from learning_resources.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from grounding.base import CertificationInfo, FoundryIQProvider, FoundryIQResult
from observability.otel import trace_iq_call

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COLLECTION_NAME = "foundry_iq_resources"
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_FIXTURES_DIR = Path(__file__).parent.parent.parent / "data" / "fixtures"


def _load_resources() -> list[dict]:
    """Load learning_resources.json and return the resources list."""
    path = _FIXTURES_DIR / "learning_resources.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["resources"]


def _load_certifications() -> list[dict]:
    """Load certification_catalog.json and return the certifications list."""
    path = _FIXTURES_DIR / "certification_catalog.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["certifications"]


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockFoundryIQProvider(FoundryIQProvider):
    """Foundry IQ backed by an in-process ChromaDB collection.

    Seeding is lazy and idempotent: the collection is populated only on the
    first method call, and only if it is empty.  This avoids any startup-time
    race condition and keeps the provider deterministic (NFR-003).

    ChromaDB client selection:
    - If the ``CHROMA_DB_PATH`` env var is set, a persistent client is used at
      that path (useful for local dev with a pre-warmed cache).
    - Otherwise an ephemeral in-memory client is used (default; safe for tests
      and CI).
    """

    # Class-level flag shared across all instances so the seed runs once per
    # process even if multiple provider instances are created.
    _seeded: ClassVar[bool] = False
    _client: ClassVar[chromadb.Client | None] = None  # type: ignore[type-arg]
    _collection: ClassVar[chromadb.Collection | None] = None  # type: ignore[type-arg]

    def __init__(self) -> None:
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _build_client(cls) -> chromadb.ClientAPI:  # type: ignore[return]
        chroma_path = os.environ.get("CHROMA_DB_PATH", "")
        if chroma_path:
            return chromadb.PersistentClient(path=chroma_path)
        return chromadb.EphemeralClient()

    @classmethod
    def _ensure_collection(cls) -> None:
        """Initialise client + collection and seed if empty (idempotent)."""
        if cls._seeded:
            return

        embed_fn = SentenceTransformerEmbeddingFunction(model_name=_EMBEDDING_MODEL)

        if cls._client is None:
            cls._client = cls._build_client()

        cls._collection = cls._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=embed_fn,  # type: ignore[arg-type]
            metadata={"hnsw:space": "cosine"},
        )

        # Only seed when the collection is empty (idempotent guard)
        if cls._collection.count() == 0:
            cls._seed(cls._collection)

        cls._seeded = True

    @staticmethod
    def _seed(collection: chromadb.Collection) -> None:  # type: ignore[type-arg]
        """Load all resources from the fixture and add them to ChromaDB."""
        resources = _load_resources()

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for res in resources:
            ids.append(res["resource_id"])
            documents.append(res["content_summary"])
            metadatas.append(
                {
                    "title": res["title"],
                    "cert_ids": ",".join(res.get("cert_ids", [])),
                    "skill_tags": ",".join(res.get("skill_tags", [])),
                    "source_url": res.get("url", ""),
                    "resource_id": res["resource_id"],
                }
            )

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    # ------------------------------------------------------------------
    # FoundryIQProvider interface
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        cert_ids: list[str] | None = None,
        k: int = 5,
    ) -> list[FoundryIQResult]:
        """Semantic search over the ChromaDB collection.

        If *cert_ids* is provided, a ``$contains`` where-clause is applied so
        that only resources tagged with at least one of those certs are
        considered.  ChromaDB's metadata filters use string matching, so cert
        IDs are stored as a comma-separated string and filtered via ``$contains``.
        """
        self._ensure_collection()
        assert self._collection is not None  # guaranteed after _ensure_collection

        where: dict | None = None
        if cert_ids:
            if len(cert_ids) == 1:
                where = {"cert_ids": {"$contains": cert_ids[0]}}
            else:
                # OR across cert ids via $or
                where = {
                    "$or": [
                        {"cert_ids": {"$contains": cid}} for cid in cert_ids
                    ]
                }

        query_kwargs: dict = {
            "query_texts": [query],
            "n_results": min(k, self._collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        output: list[FoundryIQResult] = []

        with trace_iq_call("foundry_iq", "search"):
            results = self._collection.query(**query_kwargs)

            docs = results["documents"][0]  # type: ignore[index]
            metas = results["metadatas"][0]  # type: ignore[index]
            distances = results["distances"][0]  # type: ignore[index]

            for doc, meta, dist in zip(docs, metas, distances):
                # ChromaDB cosine distance → similarity score (0=identical, 2=opposite)
                relevance = round(max(0.0, 1.0 - dist), 4)
                rid = meta.get("resource_id", "")
                title = meta.get("title", "")
                output.append(
                    FoundryIQResult(
                        resource_id=rid,
                        title=title,
                        content=doc,
                        source_url=meta.get("source_url", ""),
                        relevance_score=relevance,
                        citation=f"{rid} — {title}",
                    )
                )

        return output

    def cert_catalog(self) -> list[CertificationInfo]:
        """Return the full certification catalog from fixtures."""
        raw = _load_certifications()
        catalog: list[CertificationInfo] = []
        for c in raw:
            catalog.append(
                CertificationInfo(
                    cert_id=c["cert_id"],
                    name=c["title"],
                    skills=c.get("skill_modules", []),
                    recommended_hours=c.get("recommended_hours", 0),
                    passing_score=c.get("passing_score", 700),
                    prerequisites=c.get("prereqs", []),
                )
            )
        return catalog
