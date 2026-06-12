from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Generator

from elasticsearch import Elasticsearch, NotFoundError, RequestError, TransportError
from elasticsearch.helpers import BulkIndexError, streaming_bulk

from config.settings import get_settings
settings = get_settings() 

logger = logging.getLogger(__name__)


# ── Connection ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_es_client() -> Elasticsearch:
    """
    Returns a cached singleton Elasticsearch client.
    Uses lru_cache so the same instance is reused across the codebase.
    """
    kwargs: dict[str, Any] = {
        "hosts": [settings.ES_HOST],
        "basic_auth": (settings.ES_USERNAME, settings.ES_PASSWORD),
        "retry_on_timeout": True,
        "max_retries": 3,
        "request_timeout": 30,
        "sniff_on_start": False,
    }

    client = Elasticsearch(**kwargs)
    logger.info("Elasticsearch client initialised", extra={"host": settings.ES_HOST})
    return client


# ── Health ────────────────────────────────────────────────────────────────────

def ping() -> bool:
    """Returns True if the cluster is reachable."""
    try:
        return get_es_client().ping()
    except TransportError as exc:
        logger.error("Elasticsearch ping failed", extra={"error": str(exc)})
        return False


def health() -> dict[str, Any]:
    """Returns the cluster health dict or raises on failure."""
    return get_es_client().cluster.health()


# ── Index management ──────────────────────────────────────────────────────────

def create_index_if_not_exists(
    index: str,
    mapping: dict[str, Any],
) -> bool:
    """
    Creates an index with the given mapping if it does not already exist.
    Returns True if created, False if it already existed.
    """
    client = get_es_client()
    if client.indices.exists(index=index):
        logger.info("Index already exists, skipping creation", extra={"index": index})
        return False

    client.indices.create(index=index, body=mapping)
    logger.info("Index created", extra={"index": index})
    return True


def delete_index(index: str, ignore_missing: bool = True) -> bool:
    """
    Deletes an index.
    Returns True if deleted, False if it didn't exist and ignore_missing=True.
    """
    client = get_es_client()
    try:
        client.indices.delete(index=index)
        logger.warning("Index deleted", extra={"index": index})
        return True
    except NotFoundError:
        if ignore_missing:
            return False
        raise


# ── Bulk indexing ─────────────────────────────────────────────────────────────

def bulk_index(
    documents: list[dict[str, Any]],
    index: str | None = None,
    chunk_size: int = 500,
    raise_on_error: bool = True,
) -> tuple[int, int]:
    """
    Bulk indexes a list of documents.

    Each document should have an '_id' key for idempotent upserts.
    Returns (success_count, error_count).

    Args:
        documents:      List of dicts. Each dict may include '_id', '_index', etc.
        index:          Target index (fallback if doc has no '_index' key).
        chunk_size:     Documents per bulk request.
        raise_on_error: Raise BulkIndexError if any doc fails.
    """
    client = get_es_client()
    target_index = index or settings.ES_INDEX

    def _actions() -> Generator[dict[str, Any], None, None]:
        for doc in documents:
            action = {
                "_index": doc.pop("_index", target_index),
                "_id":    doc.pop("_id", None),
                **doc,
            }
            yield action

    success, errors = 0, 0
    try:
        for ok, info in streaming_bulk(
            client,
            _actions(),
            chunk_size=chunk_size,
            raise_on_error=False,
        ):
            if ok:
                success += 1
            else:
                errors += 1
                logger.error("Bulk index error", extra={"info": info})

        if raise_on_error and errors:
            raise BulkIndexError(f"{errors} document(s) failed to index")

    except BulkIndexError as exc:
        logger.error("Bulk indexing failed", extra={"error": str(exc)})
        raise

    logger.info(
        "Bulk indexing complete",
        extra={"success": success, "errors": errors, "index": target_index},
    )
    return success, errors


# ── Search helpers ────────────────────────────────────────────────────────────

def search(
    query: dict[str, Any],
    index: str | None = None,
    size: int = 10,
    source_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Executes a search query and returns a flat list of hit dicts.
    Each hit includes '_id', '_score', and all source fields.
    """
    client = get_es_client()
    target_index = index or settings.es_index_name

    body: dict[str, Any] = {"query": query, "size": size}
    if source_fields:
        body["_source"] = source_fields

    try:
        response = client.search(index=target_index, body=body)
    except RequestError as exc:
        logger.error("Search request failed", extra={"error": str(exc), "query": query})
        raise

    hits = response["hits"]["hits"]
    return [{"_id": h["_id"], "_score": h["_score"], **h["_source"]} for h in hits]


def knn_search(
    query_vector: list[float],
    field: str = "embedding",
    k: int | None = None,
    num_candidates: int | None = None,
    index: str | None = None,
    filter_query: dict[str, Any] | None = None,
    source_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Executes an ES kNN (approximate nearest-neighbour) search.
    Optionally applies a pre-filter (e.g. entity filter).
    Returns a flat list of hit dicts with '_id', '_score', and source fields.
    """
    client = get_es_client()
    target_index = index or settings.es_index_name

    knn_clause: dict[str, Any] = {
        "field":         field,
        "query_vector":  query_vector,
        "k":             k or settings.retrieval_top_k,
        "num_candidates": num_candidates or settings.knn_num_candidates,
    }
    if filter_query:
        knn_clause["filter"] = filter_query

    body: dict[str, Any] = {"knn": knn_clause}
    if source_fields:
        body["_source"] = source_fields

    try:
        response = client.search(index=target_index, body=body)
    except RequestError as exc:
        logger.error("kNN search failed", extra={"error": str(exc)})
        raise

    hits = response["hits"]["hits"]
    return [{"_id": h["_id"], "_score": h["_score"], **h["_source"]} for h in hits]


def get_document(doc_id: str, index: str | None = None) -> dict[str, Any] | None:
    """
    Fetches a single document by ID.
    Returns None if not found.
    """
    client = get_es_client()
    target_index = index or settings.es_index_name
    try:
        response = client.get(index=target_index, id=doc_id)
        return {"_id": response["_id"], **response["_source"]}
    except NotFoundError:
        return None