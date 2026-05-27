from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
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
class HrRetrievalResult:
    query: str
    mode: str
    results: tuple[HrContextChunk, ...]


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
) -> HrRetrievalResult:
    normalized_query = " ".join(query.split())
    if not normalized_query:
        raise HrContextValidationError("Retrieval query must be a non-empty string")

    if mode == "mock":
        chunks = context.chunks or build_retrieval_chunks(
            company_inputs=context.company_inputs,
            role_description=context.role_description,
            sources=context.sources,
        )
        return HrRetrievalResult(
            query=normalized_query,
            mode=mode,
            results=_retrieve_mock_chunks(
                chunks,
                normalized_query,
                limit=DEFAULT_MOCK_RETRIEVAL_LIMIT,
            ),
        )

    if mode == "llm":
        try:
            load_openrouter_embedding_config()
        except ValueError as exc:
            raise HrContextValidationError(str(exc)) from exc
        raise HrContextValidationError(
            "Live HR retrieval is not implemented yet; use --mode mock for deterministic retrieval"
        )

    raise HrContextValidationError("Retrieval mode must be one of: llm, mock")


def retrieval_result_to_dict(result: HrRetrievalResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "mode": result.mode,
        "results": [_retrieval_chunk_to_dict(chunk) for chunk in result.results],
    }


def _chunk_document(
    document: HrContextInputDocument,
    source: HrContextSource,
) -> list[HrContextChunk]:
    sections = _split_markdown_sections(document.markdown)
    chunks: list[HrContextChunk] = []
    for section in sections:
        chunk_text = _normalize_chunk_text(section)
        if not chunk_text:
            continue
        chunks.append(
            HrContextChunk(
                id=f"{document.source_id}_chunk_{len(chunks) + 1:03d}",
                source_id=document.source_id,
                text=chunk_text,
                metadata={
                    "source_id": source.id,
                    "source_kind": source.kind,
                    "source_title": source.title,
                    "source_uri": source.uri,
                    "content_sha256": source.content_sha256,
                    "chunk_index": str(len(chunks)),
                },
            )
        )
    return chunks


def _split_markdown_sections(markdown: str) -> list[str]:
    sections: list[list[str]] = []
    current: list[str] = []

    for line in markdown.splitlines():
        if line.startswith("## ") and current and _has_body_content(current):
            sections.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append(current)

    normalized_sections = []
    for section in sections:
        normalized = "\n".join(section).strip()
        if normalized:
            normalized_sections.append(normalized)
    return normalized_sections


def _has_body_content(lines: list[str]) -> bool:
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return True
    return False


def _normalize_chunk_text(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _retrieve_mock_chunks(
    chunks: tuple[HrContextChunk, ...],
    query: str,
    *,
    limit: int,
) -> tuple[HrContextChunk, ...]:
    query_vector = _mock_embedding(query)
    scored = []
    for position, chunk in enumerate(chunks):
        score = _cosine_similarity(query_vector, _mock_embedding(chunk.text))
        if score > 0:
            scored.append((score, position, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(chunk for _, _, chunk in scored[:limit])


def _mock_embedding(text: str) -> Counter[str]:
    return Counter(token for token in _tokenize(text) if token not in _STOP_WORDS)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0

    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    if numerator == 0:
        return 0.0

    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm)


def _retrieval_chunk_to_dict(chunk: HrContextChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "text": chunk.text,
        "metadata": dict(chunk.metadata),
    }
