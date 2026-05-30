from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import time
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
from .structured_logging import (
    duration_ms,
    exception_log_fields,
    log_structured_event,
    safe_snippet,
)

DEFAULT_MOCK_RETRIEVAL_LIMIT = 3
DEFAULT_CHUNK_SIZE_TOKENS = 350
DEFAULT_CHUNK_OVERLAP_TOKENS = 50
DEFAULT_MOCK_EMBEDDING_DIMENSIONS = 128
VECTOR_STORE_ENV_VAR = "PREPPER_HR_VECTOR_STORE_DIR"
FAISS_INDEX_MANIFEST_FILENAME = "index_manifest.json"
FAISS_INDEX_MANIFEST_SCHEMA_VERSION = "prepper-faiss-index.v1"

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
    candidate_inputs: tuple[HrContextInputDocument, ...] = (),
    summaries: Any | None = None,
    candidate_profile: Any | None = None,
    tool_results: tuple[Any, ...] = (),
    replay_metadata: Any | None = None,
    context_metadata: dict[str, Any] | None = None,
) -> tuple[HrContextChunk, ...]:
    """Build deterministic retrieval chunks for the full HR context."""
    source_by_id = {source.id: source for source in sources}
    chunks: list[HrContextChunk] = []

    document_specs: list[tuple[HrContextInputDocument, str]] = [
        *(
            (document, f"company_inputs[{index}].markdown")
            for index, document in enumerate(company_inputs)
        ),
        (role_description, "role_description.markdown"),
        *(
            (document, f"candidate_inputs[{index}].markdown")
            for index, document in enumerate(candidate_inputs)
        ),
    ]
    for document, field_path in document_specs:
        source = source_by_id.get(document.source_id)
        if source is None:
            raise HrContextValidationError(
                f"Cannot chunk document '{document.source_id}' because its source is missing"
            )
        chunks.extend(
            build_document_retrieval_chunks(
                document=document,
                source=source,
                field_path=field_path,
            )
        )

    for source, document, field_path in _build_structured_context_entries(
        summaries=summaries,
        candidate_profile=candidate_profile,
        sources=sources,
        tool_results=tool_results,
        replay_metadata=replay_metadata,
        context_metadata=context_metadata,
    ):
        chunks.extend(
            build_document_retrieval_chunks(
                document=document,
                source=source,
                field_path=field_path,
            )
        )

    return tuple(chunks)


def build_document_retrieval_chunks(
    *,
    document: HrContextInputDocument,
    source: HrContextSource,
    field_path: str | None = None,
) -> tuple[HrContextChunk, ...]:
    """Build deterministic retrieval chunks for one source-backed document."""
    return tuple(_chunk_document(document, source, field_path=field_path))


def _build_structured_context_entries(
    *,
    summaries: Any | None,
    candidate_profile: Any | None,
    sources: tuple[HrContextSource, ...],
    tool_results: tuple[Any, ...],
    replay_metadata: Any | None,
    context_metadata: dict[str, Any] | None,
) -> list[tuple[HrContextSource, HrContextInputDocument, str]]:
    entries: list[tuple[HrContextSource, HrContextInputDocument, str]] = []

    def add_entry(
        *,
        source_id: str,
        kind: str,
        title: str,
        uri: str,
        field_path: str,
        markdown: str,
    ) -> None:
        normalized = _normalize_chunk_text(markdown)
        if not normalized:
            return
        source = HrContextSource(
            id=source_id,
            kind=kind,
            title=title,
            uri=uri,
            content_sha256=_sha256_text(normalized),
        )
        document = HrContextInputDocument(
            source_id=source.id,
            title=title,
            markdown=normalized,
            summary=_summarize_retrieval_text(normalized),
        )
        entries.append((source, document, field_path))

    if context_metadata is not None:
        add_entry(
            source_id="context_metadata",
            kind="context_metadata",
            title="HR context metadata",
            uri="context://metadata",
            field_path="context_metadata",
            markdown=_json_markdown("HR context metadata", context_metadata),
        )

    if summaries is not None:
        add_entry(
            source_id="context_summaries",
            kind="summary",
            title="HR context summaries",
            uri="context://summaries",
            field_path="summaries",
            markdown=_summaries_to_markdown(summaries),
        )

    if candidate_profile is not None:
        add_entry(
            source_id="candidate_profile",
            kind="candidate_profile",
            title="Candidate profile",
            uri="context://candidate_profile",
            field_path="candidate_profile",
            markdown=_candidate_profile_to_markdown(candidate_profile),
        )

    add_entry(
        source_id="context_sources",
        kind="source_catalog",
        title="HR context source catalog",
        uri="context://sources",
        field_path="sources",
        markdown=_sources_to_markdown(sources),
    )

    for index, tool_result in enumerate(tool_results):
        tool_name = str(getattr(tool_result, "tool_name", f"tool_{index}"))
        add_entry(
            source_id=f"tool_result_{index:03d}_{_safe_path_part(tool_name)}",
            kind="tool_result",
            title=f"Tool result: {tool_name}",
            uri=f"context://tool_results/{index}",
            field_path=f"tool_results[{index}]",
            markdown=_tool_result_to_markdown(tool_result),
        )

    if replay_metadata is not None:
        add_entry(
            source_id="replay_metadata",
            kind="replay_metadata",
            title="Replay metadata",
            uri="context://replay_metadata",
            field_path="replay_metadata",
            markdown=_json_markdown("Replay metadata", replay_metadata),
        )

    return entries


def _summaries_to_markdown(summaries: Any) -> str:
    return "\n\n".join(
        (
            "# HR context summaries",
            f"## Company\n{getattr(summaries, 'company', '')}",
            f"## Role\n{getattr(summaries, 'role', '')}",
            f"## Candidate\n{getattr(summaries, 'candidate', '')}",
        )
    )


def _candidate_profile_to_markdown(profile: Any) -> str:
    sections = ["# Candidate profile"]
    for field_name, title in (
        ("skills", "Skills"),
        ("experience", "Experience"),
        ("seniority_signals", "Seniority signals"),
        ("risks", "Risks"),
        ("interview_focus_areas", "Interview focus areas"),
    ):
        values = tuple(getattr(profile, field_name, ()) or ())
        if not values:
            continue
        sections.append(f"## {title}\n" + "\n".join(f"- {value}" for value in values))
    return "\n\n".join(sections)


def _sources_to_markdown(sources: tuple[HrContextSource, ...]) -> str:
    if not sources:
        return ""
    lines = ["# HR context sources"]
    for source in sources:
        lines.extend(
            (
                f"## {source.title}",
                f"- id: {source.id}",
                f"- kind: {source.kind}",
                f"- uri: {source.uri}",
                f"- content_sha256: {source.content_sha256}",
            )
        )
    return "\n".join(lines)


def _tool_result_to_markdown(tool_result: Any) -> str:
    tool_name = str(getattr(tool_result, "tool_name", "HR tool result"))
    return _json_markdown(f"Tool result: {tool_name}", tool_result)


def _json_markdown(title: str, value: Any) -> str:
    return f"# {title}\n\n```json\n{json.dumps(_to_jsonable(value), sort_keys=True, indent=2)}\n```"


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {
            field_name: _to_jsonable(getattr(value, field_name))
            for field_name in value.__dataclass_fields__
        }
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _summarize_retrieval_text(text: str, *, max_chars: int = 280) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 3].rsplit(" ", 1)[0].rstrip()
    return f"{truncated or normalized[: max_chars - 3].rstrip()}..."


def build_candidate_fit_retrieval_chunks(
    context: HrContext,
) -> tuple[HrContextChunk, ...]:
    """Build searchable candidate evidence chunks for company/role fit retrieval."""
    source_by_id = {source.id: source for source in context.sources}
    chunks: list[HrContextChunk] = []

    for index, document in enumerate(context.candidate_inputs):
        source = source_by_id.get(document.source_id)
        if source is None:
            raise HrContextValidationError(
                f"Cannot chunk document '{document.source_id}' because its source is missing"
            )
        chunks.extend(
            build_document_retrieval_chunks(
                document=document,
                source=source,
                field_path=f"candidate_inputs[{index}].markdown",
            )
        )

    profile_markdown = _candidate_profile_to_markdown(context.candidate_profile)
    normalized_profile = _normalize_chunk_text(profile_markdown)
    if normalized_profile:
        profile_source = HrContextSource(
            id="candidate_profile",
            kind="candidate_profile",
            title="Candidate profile",
            uri="context://candidate_profile",
            content_sha256=_sha256_text(normalized_profile),
        )
        profile_document = HrContextInputDocument(
            source_id=profile_source.id,
            title=profile_source.title,
            markdown=normalized_profile,
            summary=_summarize_retrieval_text(normalized_profile),
        )
        chunks.extend(
            build_document_retrieval_chunks(
                document=profile_document,
                source=profile_source,
                field_path="candidate_profile",
            )
        )

    return tuple(chunks)


def build_candidate_fit_retrieval_query(context: HrContext, query: str) -> str:
    """Build the semantic search query used to find candidate evidence for this role."""
    normalized_query = " ".join(query.split())
    company_signal = _join_retrieval_signals(
        [
            context.summaries.company,
            *(document.title for document in context.company_inputs),
            *(document.summary for document in context.company_inputs),
        ],
        max_chars=1200,
    )
    role_signal = _join_retrieval_signals(
        [
            context.summaries.role,
            context.role_description.title,
            context.role_description.summary,
        ],
        max_chars=1200,
    )
    return "\n".join(
        line
        for line in (
            "Find candidate resume/profile evidence that is most relevant to this company and role.",
            f"Company context: {company_signal}",
            f"Role requirements: {role_signal}",
            f"Current interview query or turn: {normalized_query}",
        )
        if line.strip()
    )


def _join_retrieval_signals(values: list[str], *, max_chars: int) -> str:
    joined = " ".join(
        " ".join(value.split()) for value in values if value and value.strip()
    )
    if not joined:
        return "none"
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 1].rstrip() + "…"


def retrieve_hr_context(
    context: HrContext,
    *,
    query: str,
    mode: str = "mock",
    limit: int = DEFAULT_MOCK_RETRIEVAL_LIMIT,
    rebuild_missing_chunks: bool = True,
) -> HrRetrievalResult:
    started_at = time.monotonic()
    normalized_query = " ".join(query.split())
    log_fields: dict[str, Any] = {
        "mode": mode,
        "limit": limit,
        "context_id": context.context_id,
        "query_snippet": safe_snippet(normalized_query),
        "retrieval_scope": "candidate_fit",
        "rebuild_missing_chunks": rebuild_missing_chunks,
    }
    try:
        if not normalized_query:
            raise HrContextValidationError("Retrieval query must be a non-empty string")
        if limit <= 0:
            raise HrContextValidationError("Retrieval limit must be greater than 0")
        if mode not in {"llm", "mock"}:
            raise HrContextValidationError("Retrieval mode must be one of: llm, mock")

        chunks = (
            build_candidate_fit_retrieval_chunks(context)
            if rebuild_missing_chunks
            else _candidate_fit_chunks_from_existing(context.chunks)
        )
        search_query = build_candidate_fit_retrieval_query(context, normalized_query)
        log_fields["chunk_count"] = len(chunks)
        log_fields["search_query_snippet"] = safe_snippet(search_query)
        if not chunks:
            result = HrRetrievalResult(query=normalized_query, mode=mode, results=())
        elif mode == "mock":
            result = HrRetrievalResult(
                query=normalized_query,
                mode=mode,
                results=_retrieve_mock_chunks(
                    chunks,
                    search_query,
                    limit=limit,
                ),
            )
        elif mode == "llm":
            try:
                config = load_openrouter_embedding_config()
            except ValueError as exc:
                raise HrContextValidationError(str(exc)) from exc
            log_fields["embedding_model"] = config.embedding_model
            result = HrRetrievalResult(
                query=normalized_query,
                mode=mode,
                results=_retrieve_llm_chunks(
                    chunks,
                    search_query,
                    config=config,
                    limit=limit,
                ),
            )
        else:  # pragma: no cover - guarded above
            raise HrContextValidationError("Retrieval mode must be one of: llm, mock")
    except Exception as exc:
        log_structured_event(
            "retrieval",
            status="error",
            level=logging.WARNING,
            duration_ms=duration_ms(started_at),
            **log_fields,
            **exception_log_fields(exc),
        )
        raise

    log_structured_event(
        "retrieval",
        status="success",
        duration_ms=duration_ms(started_at),
        result_count=len(result.results),
        top_score=max((match.score for match in result.results), default=0.0),
        **log_fields,
    )
    return result


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


def _candidate_fit_chunks_from_existing(
    chunks: tuple[HrContextChunk, ...],
) -> tuple[HrContextChunk, ...]:
    candidate_field_prefix = "candidate_inputs["
    return tuple(
        chunk
        for chunk in chunks
        if chunk.metadata.get("field_path") == "candidate_profile"
        or chunk.metadata.get("field_path", "").startswith(candidate_field_prefix)
    )


def _context_metadata(context: HrContext) -> dict[str, Any]:
    return {
        "schema_version": context.schema_version,
        "context_id": context.context_id,
        "fixture_id": context.fixture_id,
        "mode": context.mode,
        "company_input_count": len(context.company_inputs),
        "candidate_input_count": len(context.candidate_inputs),
        "source_count": len(context.sources),
        "tool_result_count": len(context.tool_results),
        "replay_transcript_count": len(context.replay_metadata.transcripts),
    }



def _chunk_document(
    document: HrContextInputDocument,
    source: HrContextSource,
    *,
    field_path: str | None = None,
) -> list[HrContextChunk]:
    splitter = _build_text_splitter()
    langchain_documents = _build_langchain_documents(
        (document,),
        {source.id: source},
        field_paths={source.id: field_path} if field_path else None,
    )
    split_documents = splitter.split_documents(langchain_documents)

    chunks: list[HrContextChunk] = []
    for split_document in split_documents:
        chunk_text = _normalize_chunk_text(split_document.page_content)
        if not chunk_text:
            continue
        metadata = {
            str(key): str(value) for key, value in split_document.metadata.items()
        }
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
    *,
    field_paths: dict[str, str | None] | None = None,
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
        metadata = {
            "source_id": source.id,
            "source_kind": source.kind,
            "source_title": source.title,
            "source_uri": source.uri,
            "content_sha256": source.content_sha256,
        }
        field_path = field_paths.get(source.id) if field_paths else None
        if field_path:
            metadata["field_path"] = field_path
        langchain_documents.append(
            Document(
                page_content=document.markdown,
                metadata=metadata,
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
    embedding_base_url: str = "",
) -> tuple[HrRetrievalMatch, ...]:
    embeddings = _ensure_langchain_embeddings(embeddings)
    vector_store = _load_or_build_faiss_store(
        chunks,
        embeddings=embeddings,
        mode=mode,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
    )
    try:
        docs_and_scores = vector_store.similarity_search_with_score(query, k=limit)
    except Exception:
        # If a saved index was created with incompatible embedding dimensions or
        # metadata, rebuild from the current chunks and retry once.
        try:
            vector_store = _load_or_build_faiss_store(
                chunks,
                embeddings=embeddings,
                mode=mode,
                embedding_model=embedding_model,
                embedding_base_url=embedding_base_url,
                force_rebuild=True,
            )
            docs_and_scores = vector_store.similarity_search_with_score(query, k=limit)
        except Exception as exc:  # pragma: no cover - depends on provider/runtime
            if mode == "llm":
                raise HrContextValidationError(
                    f"Live HR retrieval failed: {exc}"
                ) from exc
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
    embedding_base_url: str = "",
    force_rebuild: bool = False,
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
        embedding_base_url=embedding_base_url,
    )
    if force_rebuild and index_dir.exists():
        shutil.rmtree(index_dir)
    if (
        not force_rebuild
        and _faiss_index_exists(index_dir)
        and _faiss_manifest_matches(
            index_dir,
            chunks=chunks,
            mode=mode,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url,
        )
    ):
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
        _write_faiss_manifest(
            index_dir,
            chunks=chunks,
            mode=mode,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url,
            vector_dimension=_faiss_vector_dimension(vector_store),
        )
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
    embedding_base_url: str = "",
) -> Path:
    return _vector_store_root() / _safe_path_part(mode) / _retrieval_index_key(
        chunks,
        mode=mode,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
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
    embedding_base_url: str = "",
) -> str:
    payload = {
        "mode": mode,
        "embedding_model": embedding_model,
        "embedding_base_url": embedding_base_url,
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


def _faiss_manifest_matches(
    index_dir: Path,
    *,
    chunks: tuple[HrContextChunk, ...],
    mode: str,
    embedding_model: str,
    embedding_base_url: str,
) -> bool:
    manifest_path = index_dir / FAISS_INDEX_MANIFEST_FILENAME
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = _faiss_manifest_payload(
        chunks=chunks,
        mode=mode,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
        vector_dimension=manifest.get("vector_dimension"),
    )
    return all(
        manifest.get(key) == expected[key]
        for key in (
            "schema_version",
            "mode",
            "embedding_model",
            "embedding_base_url",
            "chunk_size_tokens",
            "chunk_overlap_tokens",
            "chunk_count",
            "chunk_fingerprint",
        )
    )


def _write_faiss_manifest(
    index_dir: Path,
    *,
    chunks: tuple[HrContextChunk, ...],
    mode: str,
    embedding_model: str,
    embedding_base_url: str,
    vector_dimension: int | None,
) -> None:
    manifest = _faiss_manifest_payload(
        chunks=chunks,
        mode=mode,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
        vector_dimension=vector_dimension,
    )
    (index_dir / FAISS_INDEX_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _faiss_manifest_payload(
    *,
    chunks: tuple[HrContextChunk, ...],
    mode: str,
    embedding_model: str,
    embedding_base_url: str,
    vector_dimension: int | None,
) -> dict[str, Any]:
    return {
        "schema_version": FAISS_INDEX_MANIFEST_SCHEMA_VERSION,
        "mode": mode,
        "embedding_model": embedding_model,
        "embedding_base_url": embedding_base_url,
        "vector_dimension": vector_dimension,
        "chunk_size_tokens": DEFAULT_CHUNK_SIZE_TOKENS,
        "chunk_overlap_tokens": DEFAULT_CHUNK_OVERLAP_TOKENS,
        "chunk_count": len(chunks),
        "chunk_fingerprint": _retrieval_index_key(
            chunks,
            mode=mode,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url,
        ),
    }


def _faiss_vector_dimension(vector_store: Any) -> int | None:
    dimension = getattr(getattr(vector_store, "index", None), "d", None)
    return dimension if isinstance(dimension, int) else None


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
        embedding_base_url=config.base_url,
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
