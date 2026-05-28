from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import OpenRouterEmbeddingConfig, load_openrouter_embedding_config
from .hr_context import (
    HrContext,
    HrContextChunk,
    HrContextInputDocument,
    HrContextSource,
    HrContextValidationError,
)

DEFAULT_MOCK_RETRIEVAL_LIMIT = 3
DEFAULT_CHUNK_SIZE_TOKENS = 350
DEFAULT_CHUNK_OVERLAP_TOKENS = 50
DEFAULT_MOCK_EMBEDDING_DIMENSIONS = 128
VECTOR_STORE_ENV_VAR = "PREPPER_HR_VECTOR_STORE_DIR"

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class HrRetrievalMatch:
    chunk: HrContextChunk
    score: float


@dataclass(frozen=True)
class HrRetrievalResult:
    query: str
    mode: str
    results: tuple[HrRetrievalMatch, ...]


def build_retrieval_chunks(
    *,
    company_inputs: tuple[HrContextInputDocument, ...],
    role_description: HrContextInputDocument,
    sources: tuple[HrContextSource, ...],
) -> tuple[HrContextChunk, ...]:
    """Build deterministic retrieval chunks for company and role documents."""
    source_by_id = {source.id: source for source in sources}
    chunks: list[HrContextChunk] = []

    for document in (*company_inputs, role_description):
        source = source_by_id.get(document.source_id)
        if source is None:
            raise HrContextValidationError(
                f"Cannot chunk document '{document.source_id}' because its source is missing"
            )
        chunks.extend(build_document_retrieval_chunks(document=document, source=source))

    return tuple(chunks)


def build_document_retrieval_chunks(
    *,
    document: HrContextInputDocument,
    source: HrContextSource,
) -> tuple[HrContextChunk, ...]:
    """Build deterministic retrieval chunks for one source-backed document."""
    return tuple(_chunk_document(document, source))


def retrieve_hr_context(
    context: HrContext,
    *,
    query: str,
    mode: str = "mock",
    limit: int = DEFAULT_MOCK_RETRIEVAL_LIMIT,
    rebuild_missing_chunks: bool = True,
) -> HrRetrievalResult:
    normalized_query = " ".join(query.split())
    if not normalized_query:
        raise HrContextValidationError("Retrieval query must be a non-empty string")
    if limit <= 0:
        raise HrContextValidationError("Retrieval limit must be greater than 0")
    if mode not in {"llm", "mock"}:
        raise HrContextValidationError("Retrieval mode must be one of: llm, mock")

    chunks = context.chunks
    if not chunks and rebuild_missing_chunks:
        chunks = build_retrieval_chunks(
            company_inputs=context.company_inputs,
            role_description=context.role_description,
            sources=context.sources,
        )
    if not chunks:
        return HrRetrievalResult(query=normalized_query, mode=mode, results=())

    if mode == "mock":
        return HrRetrievalResult(
            query=normalized_query,
            mode=mode,
            results=_retrieve_mock_chunks(
                chunks,
                normalized_query,
                limit=limit,
            ),
        )

    if mode == "llm":
        try:
            config = load_openrouter_embedding_config()
        except ValueError as exc:
            raise HrContextValidationError(str(exc)) from exc
        return HrRetrievalResult(
            query=normalized_query,
            mode=mode,
            results=_retrieve_llm_chunks(
                chunks,
                normalized_query,
                config=config,
                limit=limit,
            ),
        )

    raise HrContextValidationError("Retrieval mode must be one of: llm, mock")


def retrieval_score_to_percent(score: float) -> int:
    """Convert a raw similarity score into a user-facing relevance percentage."""
    try:
        normalized = float(score)
    except (TypeError, ValueError):
        normalized = 0.0
    return round(max(0.0, min(1.0, normalized)) * 100)


def retrieval_result_to_dict(result: HrRetrievalResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "mode": result.mode,
        "results": [
            {
                **_retrieval_chunk_to_dict(match.chunk),
                "score": match.score,
                "relevance_percent": retrieval_score_to_percent(match.score),
                "source": _retrieval_source_to_dict(match.chunk),
            }
            for match in result.results
        ],
    }


def _chunk_document(
    document: HrContextInputDocument,
    source: HrContextSource,
) -> list[HrContextChunk]:
    splitter = _build_text_splitter()
    langchain_documents = _build_langchain_documents((document,), {source.id: source})
    split_documents = splitter.split_documents(langchain_documents)

    chunks: list[HrContextChunk] = []
    for split_document in split_documents:
        chunk_text = _normalize_chunk_text(split_document.page_content)
        if not chunk_text:
            continue
        metadata = {str(key): str(value) for key, value in split_document.metadata.items()}
        metadata["chunk_index"] = str(len(chunks))
        chunks.append(
            HrContextChunk(
                id=f"{document.source_id}_chunk_{len(chunks) + 1:03d}",
                source_id=document.source_id,
                text=chunk_text,
                metadata=metadata,
            )
        )
    return chunks


def _normalize_chunk_text(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _build_text_splitter():
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise HrContextValidationError(
            "langchain-text-splitters is required for HR retrieval chunking"
        ) from exc

    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP_TOKENS,
        add_start_index=True,
    )


def _build_langchain_documents(
    documents: tuple[HrContextInputDocument, ...],
    source_by_id: dict[str, HrContextSource],
):
    try:
        from langchain_core.documents import Document
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise HrContextValidationError(
            "langchain-core is required for HR retrieval documents"
        ) from exc

    langchain_documents = []
    for document in documents:
        source = source_by_id.get(document.source_id)
        if source is None:
            raise HrContextValidationError(
                f"Cannot chunk document '{document.source_id}' because its source is missing"
            )
        langchain_documents.append(
            Document(
                page_content=document.markdown,
                metadata={
                    "source_id": source.id,
                    "source_kind": source.kind,
                    "source_title": source.title,
                    "source_uri": source.uri,
                    "content_sha256": source.content_sha256,
                },
            )
        )
    return langchain_documents


def _retrieve_faiss_matches(
    chunks: tuple[HrContextChunk, ...],
    query: str,
    *,
    embeddings,
    mode: str,
    embedding_model: str,
    limit: int,
) -> tuple[HrRetrievalMatch, ...]:
    embeddings = _ensure_langchain_embeddings(embeddings)
    vector_store = _load_or_build_faiss_store(
        chunks,
        embeddings=embeddings,
        mode=mode,
        embedding_model=embedding_model,
    )
    try:
        docs_and_scores = vector_store.similarity_search_with_score(query, k=limit)
    except Exception as exc:  # pragma: no cover - depends on provider/runtime
        if mode == "llm":
            raise HrContextValidationError(f"Live HR retrieval failed: {exc}") from exc
        raise HrContextValidationError(f"HR retrieval failed: {exc}") from exc

    matches: list[HrRetrievalMatch] = []
    for document, raw_score in docs_and_scores:
        chunk = _chunk_from_langchain_document(document)
        score = _distance_to_similarity_score(raw_score)
        if score > 0:
            matches.append(HrRetrievalMatch(chunk=chunk, score=score))
    return tuple(matches)


def _load_or_build_faiss_store(
    chunks: tuple[HrContextChunk, ...],
    *,
    embeddings,
    mode: str,
    embedding_model: str,
):
    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise HrContextValidationError(
            "langchain-community and faiss-cpu are required for HR retrieval"
        ) from exc

    index_dir = _faiss_index_dir(
        chunks,
        mode=mode,
        embedding_model=embedding_model,
    )
    if _faiss_index_exists(index_dir):
        try:
            return FAISS.load_local(
                str(index_dir),
                embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception:
            # Stale/corrupt indexes are rebuilt from the current context chunks.
            pass

    documents = _chunks_to_langchain_documents(chunks)
    try:
        vector_store = FAISS.from_documents(
            documents,
            embeddings,
            ids=[chunk.id for chunk in chunks],
        )
        index_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(index_dir))
    except Exception as exc:  # pragma: no cover - depends on provider/runtime
        if mode == "llm":
            raise HrContextValidationError(f"Live HR retrieval failed: {exc}") from exc
        raise HrContextValidationError(f"HR retrieval failed: {exc}") from exc
    return vector_store


def _chunks_to_langchain_documents(chunks: tuple[HrContextChunk, ...]):
    try:
        from langchain_core.documents import Document
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise HrContextValidationError(
            "langchain-core is required for HR retrieval documents"
        ) from exc

    return [
        Document(
            page_content=chunk.text,
            metadata={
                **dict(chunk.metadata),
                "chunk_id": chunk.id,
                "chunk_source_id": chunk.source_id,
            },
        )
        for chunk in chunks
    ]


def _chunk_from_langchain_document(document) -> HrContextChunk:
    metadata = {str(key): str(value) for key, value in document.metadata.items()}
    chunk_id = metadata.pop("chunk_id", "")
    source_id = metadata.pop("chunk_source_id", metadata.get("source_id", ""))
    return HrContextChunk(
        id=chunk_id,
        source_id=source_id,
        text=document.page_content,
        metadata=metadata,
    )


def _faiss_index_dir(
    chunks: tuple[HrContextChunk, ...],
    *,
    mode: str,
    embedding_model: str,
) -> Path:
    return _vector_store_root() / _safe_path_part(mode) / _retrieval_index_key(
        chunks,
        mode=mode,
        embedding_model=embedding_model,
    )


def _vector_store_root() -> Path:
    configured = os.environ.get(VECTOR_STORE_ENV_VAR, "").strip()
    if configured:
        return Path(configured)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "backend" / "data" / "faiss"


def _retrieval_index_key(
    chunks: tuple[HrContextChunk, ...],
    *,
    mode: str,
    embedding_model: str,
) -> str:
    payload = {
        "mode": mode,
        "embedding_model": embedding_model,
        "chunk_size_tokens": DEFAULT_CHUNK_SIZE_TOKENS,
        "chunk_overlap_tokens": DEFAULT_CHUNK_OVERLAP_TOKENS,
        "chunks": [
            {
                "id": chunk.id,
                "source_id": chunk.source_id,
                "text_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                "metadata": dict(sorted(chunk.metadata.items())),
            }
            for chunk in chunks
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _safe_path_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._") or "default"


def _faiss_index_exists(index_dir: Path) -> bool:
    return (index_dir / "index.faiss").exists() and (index_dir / "index.pkl").exists()


def _distance_to_similarity_score(raw_score: Any) -> float:
    try:
        distance = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    if distance < 0:
        return 0.0
    return 1.0 / (1.0 + distance)


def _ensure_langchain_embeddings(embeddings):
    try:
        from langchain_core.embeddings import Embeddings
    except ImportError:  # pragma: no cover - langchain-core dependency
        return embeddings

    if isinstance(embeddings, Embeddings):
        return embeddings

    class EmbeddingsAdapter(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return embeddings.embed_documents(texts)

        def embed_query(self, text: str) -> list[float]:
            return embeddings.embed_query(text)

    return EmbeddingsAdapter()


class MockHrEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * DEFAULT_MOCK_EMBEDDING_DIMENSIONS
        for token in _tokenize(text):
            if token in _STOP_WORDS:
                continue
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % DEFAULT_MOCK_EMBEDDING_DIMENSIONS
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def _retrieve_mock_chunks(
    chunks: tuple[HrContextChunk, ...],
    query: str,
    *,
    limit: int,
) -> tuple[HrRetrievalMatch, ...]:
    embeddings = MockHrEmbeddings()
    return _retrieve_faiss_matches(
        chunks,
        query,
        embeddings=embeddings,
        mode="mock",
        embedding_model="mock-hashing-v1",
        limit=limit,
    )


def _retrieve_llm_chunks(
    chunks: tuple[HrContextChunk, ...],
    query: str,
    *,
    config: OpenRouterEmbeddingConfig,
    limit: int,
) -> tuple[HrRetrievalMatch, ...]:
    embeddings = _build_openrouter_embeddings(config)
    return _retrieve_faiss_matches(
        chunks,
        query,
        embeddings=embeddings,
        mode="llm",
        embedding_model=config.embedding_model,
        limit=limit,
    )


def _build_openrouter_embeddings(config: OpenRouterEmbeddingConfig):
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError as exc:  # pragma: no cover - depends on optional env install
        raise HrContextValidationError(
            "langchain-openai is required for HR retrieval in llm mode"
        ) from exc

    return OpenAIEmbeddings(
        model=config.embedding_model,
        api_key=config.api_key,
        base_url=config.base_url,
        check_embedding_ctx_length=False,
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _retrieval_chunk_to_dict(chunk: HrContextChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "text": chunk.text,
        "metadata": dict(chunk.metadata),
    }


def _retrieval_source_to_dict(chunk: HrContextChunk) -> dict[str, str]:
    metadata = dict(chunk.metadata)
    return {
        "id": str(metadata.get("source_id") or chunk.source_id),
        "kind": str(metadata.get("source_kind") or ""),
        "title": str(metadata.get("source_title") or chunk.source_id),
        "uri": str(metadata.get("source_uri") or ""),
    }
