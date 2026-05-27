from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hr_fixtures import HrFixture, Transcript


HR_CONTEXT_SCHEMA_VERSION = "hr-context.v1"
SUPPORTED_HR_CONTEXT_MODES = {"mock", "llm"}


@dataclass(frozen=True)
class HrContextSource:
    id: str
    kind: str
    title: str
    uri: str
    content_sha256: str


@dataclass(frozen=True)
class HrContextInputDocument:
    source_id: str
    title: str
    markdown: str
    summary: str


@dataclass(frozen=True)
class HrContextSummaries:
    company: str
    role: str
    candidate: str


@dataclass(frozen=True)
class HrContextChunk:
    id: str
    source_id: str
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class HrToolResult:
    tool_name: str
    status: str
    output: dict[str, Any]


@dataclass(frozen=True)
class HrReplayTranscriptMetadata:
    candidate: str
    transcript_uri: str
    turn_count: int
    tool_event_count: int
    source_count: int
    expected_overall_score: float
    expected_passed: bool


@dataclass(frozen=True)
class HrReplayMetadata:
    transcripts: tuple[HrReplayTranscriptMetadata, ...]


@dataclass(frozen=True)
class HrContext:
    schema_version: str
    context_id: str
    fixture_id: str | None
    mode: str
    company_inputs: tuple[HrContextInputDocument, ...]
    role_description: HrContextInputDocument
    candidate_inputs: tuple[HrContextInputDocument, ...]
    summaries: HrContextSummaries
    sources: tuple[HrContextSource, ...]
    chunks: tuple[HrContextChunk, ...]
    tool_results: tuple[HrToolResult, ...]
    replay_metadata: HrReplayMetadata


class HrContextValidationError(ValueError):
    """Raised when an HR context payload is malformed."""


def build_hr_context_from_fixture(fixture: HrFixture, *, mode: str = "mock") -> HrContext:
    if mode != "mock":
        raise HrContextValidationError(
            f"HR context fixture builds currently support only mock mode, got '{mode}'"
        )
    return build_mock_hr_context(fixture)


def build_mock_hr_context(fixture: HrFixture) -> HrContext:
    """Build a deterministic HR context from fixture files only."""
    context_id = _build_context_id(fixture, mode="mock")

    company_document = _build_input_document(
        source_id="company",
        title_fallback="Company input",
        markdown=fixture.company_markdown,
    )
    role_document = _build_input_document(
        source_id="role",
        title_fallback="Role description",
        markdown=fixture.role_markdown,
    )
    resume_document = _build_input_document(
        source_id="resume",
        title_fallback="Candidate resume",
        markdown=fixture.resume_markdown,
    )
    profile_document = _build_input_document(
        source_id="profile",
        title_fallback="Candidate profile",
        markdown=fixture.profile_markdown,
    )

    input_sources = (
        _build_source(
            id="company",
            kind="company",
            title=company_document.title,
            uri="fixture://company.md",
            content=fixture.company_markdown,
        ),
        _build_source(
            id="role",
            kind="role",
            title=role_document.title,
            uri="fixture://role.md",
            content=fixture.role_markdown,
        ),
        _build_source(
            id="resume",
            kind="resume",
            title=resume_document.title,
            uri="fixture://resume.md",
            content=fixture.resume_markdown,
        ),
        _build_source(
            id="profile",
            kind="profile",
            title=profile_document.title,
            uri="fixture://profile.md",
            content=fixture.profile_markdown,
        ),
    )

    transcript_sources = tuple(
        _build_source(
            id=f"transcript_{candidate}",
            kind="transcript",
            title=f"{candidate.title()} replay transcript",
            uri=_transcript_uri(candidate),
            content=_transcript_raw_text(fixture, candidate, transcript),
        )
        for candidate, transcript in sorted(fixture.transcripts.items())
    )

    replay_metadata = HrReplayMetadata(
        transcripts=tuple(
            _build_replay_transcript_metadata(candidate, transcript)
            for candidate, transcript in sorted(fixture.transcripts.items())
        )
    )

    sources = input_sources + transcript_sources

    from .hr_retrieval import build_retrieval_chunks

    chunks = build_retrieval_chunks(
        company_inputs=(company_document,),
        role_description=role_document,
        sources=sources,
    )

    return HrContext(
        schema_version=HR_CONTEXT_SCHEMA_VERSION,
        context_id=context_id,
        fixture_id=fixture.id,
        mode="mock",
        company_inputs=(company_document,),
        role_description=role_document,
        candidate_inputs=(resume_document, profile_document),
        summaries=HrContextSummaries(
            company=company_document.summary,
            role=role_document.summary,
            candidate=_truncate_text(
                f"{resume_document.summary} {profile_document.summary}",
                max_chars=420,
            ),
        ),
        sources=sources,
        chunks=chunks,
        tool_results=(),
        replay_metadata=replay_metadata,
    )


def hr_context_to_dict(context: HrContext) -> dict[str, Any]:
    return {
        "schema_version": context.schema_version,
        "context_id": context.context_id,
        "fixture_id": context.fixture_id,
        "mode": context.mode,
        "company_inputs": [
            _input_document_to_dict(document) for document in context.company_inputs
        ],
        "role_description": _input_document_to_dict(context.role_description),
        "candidate_inputs": [
            _input_document_to_dict(document) for document in context.candidate_inputs
        ],
        "summaries": _summaries_to_dict(context.summaries),
        "sources": [_source_to_dict(source) for source in context.sources],
        "chunks": [_chunk_to_dict(chunk) for chunk in context.chunks],
        "tool_results": [
            _tool_result_to_dict(tool_result) for tool_result in context.tool_results
        ],
        "replay_metadata": _replay_metadata_to_dict(context.replay_metadata),
    }


def hr_context_from_dict(payload: Mapping[str, Any]) -> HrContext:
    if not isinstance(payload, Mapping):
        raise HrContextValidationError("HR context payload must be an object")

    schema_version = _require_str(payload, "schema_version", "HR context")
    if schema_version != HR_CONTEXT_SCHEMA_VERSION:
        raise HrContextValidationError(
            f"Unsupported HR context schema_version '{schema_version}'"
        )

    mode = _require_str(payload, "mode", "HR context")
    if mode not in SUPPORTED_HR_CONTEXT_MODES:
        modes = ", ".join(sorted(SUPPORTED_HR_CONTEXT_MODES))
        raise HrContextValidationError(
            f"HR context field 'mode' must be one of: {modes}"
        )

    company_inputs = tuple(
        _dict_to_input_document(item, f"company_inputs[{index}]")
        for index, item in enumerate(
            _require_list(payload, "company_inputs", "HR context")
        )
    )
    if not company_inputs:
        raise HrContextValidationError(
            "HR context field 'company_inputs' must include at least one document"
        )

    candidate_inputs = tuple(
        _dict_to_input_document(item, f"candidate_inputs[{index}]")
        for index, item in enumerate(
            _require_list(payload, "candidate_inputs", "HR context")
        )
    )
    if not candidate_inputs:
        raise HrContextValidationError(
            "HR context field 'candidate_inputs' must include at least one document"
        )

    sources = tuple(
        _dict_to_source(item, f"sources[{index}]")
        for index, item in enumerate(_require_list(payload, "sources", "HR context"))
    )
    if not sources:
        raise HrContextValidationError(
            "HR context field 'sources' must include at least one source"
        )

    return HrContext(
        schema_version=schema_version,
        context_id=_require_str(payload, "context_id", "HR context"),
        fixture_id=_require_optional_str(payload, "fixture_id", "HR context"),
        mode=mode,
        company_inputs=company_inputs,
        role_description=_dict_to_input_document(
            _require_mapping(payload, "role_description", "HR context"),
            "role_description",
        ),
        candidate_inputs=candidate_inputs,
        summaries=_dict_to_summaries(
            _require_mapping(payload, "summaries", "HR context")
        ),
        sources=sources,
        chunks=tuple(
            _dict_to_chunk(item, f"chunks[{index}]")
            for index, item in enumerate(_require_list(payload, "chunks", "HR context"))
        ),
        tool_results=tuple(
            _dict_to_tool_result(item, f"tool_results[{index}]")
            for index, item in enumerate(
                _require_list(payload, "tool_results", "HR context")
            )
        ),
        replay_metadata=_dict_to_replay_metadata(
            _require_mapping(payload, "replay_metadata", "HR context")
        ),
    )


def hr_context_to_json(context: HrContext) -> str:
    return json.dumps(hr_context_to_dict(context), indent=2, sort_keys=True) + "\n"


def hr_context_from_json(raw: str) -> HrContext:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HrContextValidationError(f"Invalid HR context JSON: {exc.msg}") from exc
    return hr_context_from_dict(payload)


def write_hr_context(context: HrContext, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(hr_context_to_json(context), encoding="utf-8")
    return output_path


def load_hr_context(path: Path | str) -> HrContext:
    context_path = Path(path)
    return hr_context_from_json(context_path.read_text(encoding="utf-8"))


def _build_input_document(
    *, source_id: str, title_fallback: str, markdown: str
) -> HrContextInputDocument:
    return HrContextInputDocument(
        source_id=source_id,
        title=_first_heading(markdown, title_fallback),
        markdown=markdown,
        summary=_summarize_markdown(markdown),
    )


def _build_source(
    *, id: str, kind: str, title: str, uri: str, content: str
) -> HrContextSource:
    return HrContextSource(
        id=id,
        kind=kind,
        title=title,
        uri=uri,
        content_sha256=_sha256_text(content),
    )


def _build_replay_transcript_metadata(
    candidate: str, transcript: Transcript
) -> HrReplayTranscriptMetadata:
    return HrReplayTranscriptMetadata(
        candidate=candidate,
        transcript_uri=_transcript_uri(candidate),
        turn_count=len(transcript.turns),
        tool_event_count=len(transcript.tool_events),
        source_count=len(transcript.sources),
        expected_overall_score=transcript.expected_final_result.overall_score,
        expected_passed=transcript.expected_final_result.passed,
    )


def _build_context_id(fixture: HrFixture, *, mode: str) -> str:
    transcript_hashes = {
        candidate: _sha256_text(_transcript_raw_text(fixture, candidate, transcript))
        for candidate, transcript in sorted(fixture.transcripts.items())
    }
    fingerprint_payload = {
        "schema_version": HR_CONTEXT_SCHEMA_VERSION,
        "fixture_id": fixture.id,
        "mode": mode,
        "company_sha256": _sha256_text(fixture.company_markdown),
        "role_sha256": _sha256_text(fixture.role_markdown),
        "resume_sha256": _sha256_text(fixture.resume_markdown),
        "profile_sha256": _sha256_text(fixture.profile_markdown),
        "transcript_sha256": transcript_hashes,
    }
    fingerprint = json.dumps(
        fingerprint_payload, sort_keys=True, separators=(",", ":")
    )
    return f"hrctx_{fixture.id}_{_sha256_text(fingerprint)[:12]}"


def _transcript_uri(candidate: str) -> str:
    return f"fixture://transcripts/{candidate}.md"


def _transcript_raw_text(
    fixture: HrFixture, candidate: str, transcript: Transcript
) -> str:
    transcript_path = fixture.path / "transcripts" / f"{candidate}.md"
    if transcript_path.is_file():
        return transcript_path.read_text(encoding="utf-8")
    return json.dumps(
        {
            "fixture_id": transcript.fixture_id,
            "candidate": transcript.candidate,
            "turns": [turn.__dict__ for turn in transcript.turns],
            "tool_events": [event.__dict__ for event in transcript.tool_events],
            "sources": [source.__dict__ for source in transcript.sources],
            "expected_final_result": transcript.expected_final_result.__dict__,
            "metadata": transcript.metadata,
        },
        sort_keys=True,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return fallback


def _summarize_markdown(markdown: str, *, max_chars: int = 280) -> str:
    lines = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        if line:
            lines.append(line)
        if len(lines) >= 5:
            break
    return _truncate_text(" ".join(lines), max_chars=max_chars)


def _truncate_text(text: str, *, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 3].rsplit(" ", 1)[0].rstrip()
    if not truncated:
        truncated = normalized[: max_chars - 3].rstrip()
    return f"{truncated}..."


def _source_to_dict(source: HrContextSource) -> dict[str, str]:
    return {
        "id": source.id,
        "kind": source.kind,
        "title": source.title,
        "uri": source.uri,
        "content_sha256": source.content_sha256,
    }


def _input_document_to_dict(document: HrContextInputDocument) -> dict[str, str]:
    return {
        "source_id": document.source_id,
        "title": document.title,
        "markdown": document.markdown,
        "summary": document.summary,
    }


def _summaries_to_dict(summaries: HrContextSummaries) -> dict[str, str]:
    return {
        "company": summaries.company,
        "role": summaries.role,
        "candidate": summaries.candidate,
    }


def _chunk_to_dict(chunk: HrContextChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "text": chunk.text,
        "metadata": dict(chunk.metadata),
    }


def _tool_result_to_dict(tool_result: HrToolResult) -> dict[str, Any]:
    return {
        "tool_name": tool_result.tool_name,
        "status": tool_result.status,
        "output": dict(tool_result.output),
    }


def _replay_metadata_to_dict(metadata: HrReplayMetadata) -> dict[str, Any]:
    return {
        "transcripts": [
            _replay_transcript_metadata_to_dict(transcript)
            for transcript in metadata.transcripts
        ]
    }


def _replay_transcript_metadata_to_dict(
    metadata: HrReplayTranscriptMetadata,
) -> dict[str, Any]:
    return {
        "candidate": metadata.candidate,
        "transcript_uri": metadata.transcript_uri,
        "turn_count": metadata.turn_count,
        "tool_event_count": metadata.tool_event_count,
        "source_count": metadata.source_count,
        "expected_overall_score": metadata.expected_overall_score,
        "expected_passed": metadata.expected_passed,
    }


def _dict_to_source(value: Any, field_path: str) -> HrContextSource:
    data = _as_mapping(value, field_path)
    return HrContextSource(
        id=_require_str(data, "id", field_path),
        kind=_require_str(data, "kind", field_path),
        title=_require_str(data, "title", field_path),
        uri=_require_str(data, "uri", field_path),
        content_sha256=_require_str(data, "content_sha256", field_path),
    )


def _dict_to_input_document(value: Any, field_path: str) -> HrContextInputDocument:
    data = _as_mapping(value, field_path)
    return HrContextInputDocument(
        source_id=_require_str(data, "source_id", field_path),
        title=_require_str(data, "title", field_path),
        markdown=_require_str(data, "markdown", field_path),
        summary=_require_str(data, "summary", field_path),
    )


def _dict_to_summaries(data: Mapping[str, Any]) -> HrContextSummaries:
    return HrContextSummaries(
        company=_require_str(data, "company", "summaries"),
        role=_require_str(data, "role", "summaries"),
        candidate=_require_str(data, "candidate", "summaries"),
    )


def _dict_to_chunk(value: Any, field_path: str) -> HrContextChunk:
    data = _as_mapping(value, field_path)
    return HrContextChunk(
        id=_require_str(data, "id", field_path),
        source_id=_require_str(data, "source_id", field_path),
        text=_require_str(data, "text", field_path),
        metadata=_require_str_mapping(data, "metadata", field_path),
    )


def _dict_to_tool_result(value: Any, field_path: str) -> HrToolResult:
    data = _as_mapping(value, field_path)
    output = _require_mapping(data, "output", field_path)
    return HrToolResult(
        tool_name=_require_str(data, "tool_name", field_path),
        status=_require_str(data, "status", field_path),
        output=dict(output),
    )


def _dict_to_replay_metadata(data: Mapping[str, Any]) -> HrReplayMetadata:
    return HrReplayMetadata(
        transcripts=tuple(
            _dict_to_replay_transcript_metadata(item, f"replay_metadata.transcripts[{index}]")
            for index, item in enumerate(
                _require_list(data, "transcripts", "replay_metadata")
            )
        )
    )


def _dict_to_replay_transcript_metadata(
    value: Any, field_path: str
) -> HrReplayTranscriptMetadata:
    data = _as_mapping(value, field_path)
    return HrReplayTranscriptMetadata(
        candidate=_require_str(data, "candidate", field_path),
        transcript_uri=_require_str(data, "transcript_uri", field_path),
        turn_count=_require_int(data, "turn_count", field_path, minimum=0),
        tool_event_count=_require_int(data, "tool_event_count", field_path, minimum=0),
        source_count=_require_int(data, "source_count", field_path, minimum=0),
        expected_overall_score=_require_float(
            data, "expected_overall_score", field_path
        ),
        expected_passed=_require_bool(data, "expected_passed", field_path),
    )


def _as_mapping(value: Any, field_path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be an object"
        )
    return value


def _require_mapping(
    data: Mapping[str, Any], key: str, parent_path: str
) -> Mapping[str, Any]:
    value = _require_field(data, key, parent_path)
    return _as_mapping(value, _join_field(parent_path, key))


def _require_str_mapping(
    data: Mapping[str, Any], key: str, parent_path: str
) -> dict[str, str]:
    mapping = _require_mapping(data, key, parent_path)
    result: dict[str, str] = {}
    field_path = _join_field(parent_path, key)
    for item_key, item_value in mapping.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            raise HrContextValidationError(
                f"HR context field '{field_path}' must contain only string keys and values"
            )
        result[item_key] = item_value
    return result


def _require_list(data: Mapping[str, Any], key: str, parent_path: str) -> list[Any]:
    value = _require_field(data, key, parent_path)
    if not isinstance(value, list):
        raise HrContextValidationError(
            f"HR context field '{_join_field(parent_path, key)}' must be a list"
        )
    return value


def _require_str(data: Mapping[str, Any], key: str, parent_path: str) -> str:
    value = _require_field(data, key, parent_path)
    field_path = _join_field(parent_path, key)
    if not isinstance(value, str) or not value.strip():
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be a non-empty string"
        )
    return value


def _require_optional_str(
    data: Mapping[str, Any], key: str, parent_path: str
) -> str | None:
    value = _require_field(data, key, parent_path)
    if value is None:
        return None
    field_path = _join_field(parent_path, key)
    if not isinstance(value, str) or not value.strip():
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be null or a non-empty string"
        )
    return value


def _require_int(
    data: Mapping[str, Any], key: str, parent_path: str, *, minimum: int | None = None
) -> int:
    value = _require_field(data, key, parent_path)
    field_path = _join_field(parent_path, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be an integer"
        )
    if minimum is not None and value < minimum:
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be at least {minimum}"
        )
    return value


def _require_float(data: Mapping[str, Any], key: str, parent_path: str) -> float:
    value = _require_field(data, key, parent_path)
    field_path = _join_field(parent_path, key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be a number"
        )
    return float(value)


def _require_bool(data: Mapping[str, Any], key: str, parent_path: str) -> bool:
    value = _require_field(data, key, parent_path)
    field_path = _join_field(parent_path, key)
    if not isinstance(value, bool):
        raise HrContextValidationError(
            f"HR context field '{field_path}' must be true or false"
        )
    return value


def _require_field(data: Mapping[str, Any], key: str, parent_path: str) -> Any:
    if key not in data:
        raise HrContextValidationError(
            f"HR context field '{_join_field(parent_path, key)}' is required"
        )
    return data[key]


def _join_field(parent_path: str, key: str) -> str:
    return f"{parent_path}.{key}" if parent_path else key
