from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hr_fixtures import HrFixture, Transcript


HR_CONTEXT_SCHEMA_VERSION = "hr-context.v2"
SUPPORTED_HR_CONTEXT_SCHEMA_VERSIONS = {"hr-context.v1", HR_CONTEXT_SCHEMA_VERSION}
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
class HrCandidateProfile:
    skills: tuple[str, ...]
    experience: tuple[str, ...]
    seniority_signals: tuple[str, ...]
    risks: tuple[str, ...]
    interview_focus_areas: tuple[str, ...]


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
    candidate_profile: HrCandidateProfile
    sources: tuple[HrContextSource, ...]
    chunks: tuple[HrContextChunk, ...]
    tool_results: tuple[HrToolResult, ...]
    replay_metadata: HrReplayMetadata


@dataclass(frozen=True)
class HrContextBuildIssue:
    tool_name: str
    message: str


@dataclass(frozen=True)
class HrContextBuildResult:
    context: HrContext | None
    tool_results: tuple[HrToolResult, ...]
    errors: tuple[HrContextBuildIssue, ...]
    tool_call_events: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        return "partial" if self.errors else "success"


class HrContextValidationError(ValueError):
    """Raised when an HR context payload is malformed."""


def build_hr_context_from_fixture(fixture: HrFixture, *, mode: str = "mock") -> HrContext:
    if mode != "mock":
        raise HrContextValidationError(
            f"HR context fixture builds currently support only mock mode, got '{mode}'"
        )
    return build_mock_hr_context(fixture)


def build_hr_context_from_inputs(
    *,
    mode: str,
    role_description: str,
    resume_text: str,
    company_text: str | None = None,
    company_url: str | None = None,
    profile_text: str | None = None,
    model: str | None = None,
    fixture_id: str | None = None,
    source_uris: Mapping[str, str] | None = None,
    tool_event_recorder: Any | None = None,
) -> HrContextBuildResult:
    """Build an HR context from untrusted API/UI input text."""
    if mode not in SUPPORTED_HR_CONTEXT_MODES:
        modes = ", ".join(sorted(SUPPORTED_HR_CONTEXT_MODES))
        raise HrContextValidationError(f"HR context mode must be one of: {modes}")

    normalized_company_text = _optional_non_empty_text(company_text)
    normalized_company_url = _optional_non_empty_text(company_url)
    if bool(normalized_company_text) == bool(normalized_company_url):
        raise HrContextValidationError(
            "Exactly one of company_text or company_url is required"
        )

    normalized_role = _required_input_text(role_description, "role_description")
    normalized_resume = _required_input_text(resume_text, "resume_text")
    normalized_profile = (profile_text or "").strip()

    tool_results: list[HrToolResult] = []
    errors: list[HrContextBuildIssue] = []

    if normalized_company_text is not None:
        company_document = _build_input_document(
            source_id="company",
            title_fallback="Company input",
            markdown=normalized_company_text,
        )
        company_source = _build_source(
            id="company",
            kind="company",
            title=company_document.title,
            uri=_source_uri(source_uris, "company", "input://company_text"),
            content=normalized_company_text,
        )
    else:
        from .hr_tools import (
            FETCH_COMPANY_WEBSITE_TOOL_NAME,
            company_website_tool_result_to_context_entries,
            run_fetch_company_website_tool,
        )

        try:
            if mode == "llm" and tool_event_recorder is not None:
                from .hr_langchain_tools import create_fetch_company_website_tool

                company_tool_result = _invoke_context_langchain_tool(
                    tool=create_fetch_company_website_tool(recorder=tool_event_recorder),
                    args={"url": normalized_company_url},
                    model=model,
                    instruction="Fetch company website context for an HR candidate-fit interview.",
                )
            else:
                started_at = time.monotonic()
                try:
                    company_tool_result = run_fetch_company_website_tool(
                        mode="llm",
                        url=normalized_company_url,
                    )
                except Exception as exc:
                    from .hr_langchain_tools import record_hr_tool_result

                    record_hr_tool_result(
                        recorder=tool_event_recorder,
                        tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
                        started_at=started_at,
                        input_payload={"url": normalized_company_url},
                        error=exc,
                    )
                    raise
                from .hr_langchain_tools import record_hr_tool_result

                record_hr_tool_result(
                    recorder=tool_event_recorder,
                    tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
                    started_at=started_at,
                    input_payload={"url": normalized_company_url},
                    result=company_tool_result,
                )
            tool_results.append(company_tool_result)
            company_source, company_document, _company_chunks = (
                company_website_tool_result_to_context_entries(company_tool_result)
            )
        except Exception as exc:
            message = str(exc)
            errors.append(
                HrContextBuildIssue(
                    tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
                    message=message,
                )
            )
            tool_results.append(
                _build_failed_tool_result(
                    tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
                    mode="llm",
                    message=message,
                    extra={"url": normalized_company_url},
                )
            )
            return HrContextBuildResult(
                context=None,
                tool_results=tuple(tool_results),
                errors=tuple(errors),
                tool_call_events=tuple(
                    tool_event_recorder.to_public_dicts() if tool_event_recorder else []
                ),
            )

    role_document = _build_input_document(
        source_id="role",
        title_fallback="Role description",
        markdown=normalized_role,
    )
    resume_document = _build_input_document(
        source_id="resume",
        title_fallback="Candidate resume",
        markdown=normalized_resume,
    )
    candidate_inputs = [resume_document]
    profile_source: HrContextSource | None = None
    if normalized_profile:
        profile_document = _build_input_document(
            source_id="profile",
            title_fallback="Candidate profile",
            markdown=normalized_profile,
        )
        candidate_inputs.append(profile_document)
        profile_source = _build_source(
            id="profile",
            kind="profile",
            title=profile_document.title,
            uri=_source_uri(source_uris, "profile", "input://profile_text"),
            content=normalized_profile,
        )

    role_source = _build_source(
        id="role",
        kind="role",
        title=role_document.title,
        uri=_source_uri(source_uris, "role", "input://role_description"),
        content=normalized_role,
    )
    resume_source = _build_source(
        id="resume",
        kind="resume",
        title=resume_document.title,
        uri=_source_uri(source_uris, "resume", "input://resume_text"),
        content=normalized_resume,
    )

    from .hr_tools import (
        EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
        candidate_profile_tool_result_to_profile,
        run_extract_candidate_profile_tool,
    )

    try:
        if mode == "llm" and tool_event_recorder is not None:
            from .hr_langchain_tools import create_extract_candidate_profile_tool

            candidate_profile_result = _invoke_context_langchain_tool(
                tool=create_extract_candidate_profile_tool(
                    recorder=tool_event_recorder,
                    model=model,
                ),
                args={
                    "resume_text": normalized_resume,
                    "profile_text": normalized_profile,
                },
                model=model,
                instruction="Extract candidate profile facts for HR interview preparation.",
            )
        else:
            started_at = time.monotonic()
            try:
                candidate_profile_result = run_extract_candidate_profile_tool(
                    mode=mode,
                    resume_text=normalized_resume,
                    profile_text=normalized_profile,
                    model=model,
                )
            except Exception as exc:
                from .hr_langchain_tools import record_hr_tool_result

                record_hr_tool_result(
                    recorder=tool_event_recorder,
                    tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
                    started_at=started_at,
                    input_payload={
                        "resume_text": normalized_resume,
                        "profile_text": normalized_profile,
                    },
                    error=exc,
                )
                raise
            from .hr_langchain_tools import record_hr_tool_result

            record_hr_tool_result(
                recorder=tool_event_recorder,
                tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
                started_at=started_at,
                input_payload={
                    "resume_text": normalized_resume,
                    "profile_text": normalized_profile,
                },
                result=candidate_profile_result,
            )
        tool_results.append(candidate_profile_result)
        candidate_profile = candidate_profile_tool_result_to_profile(
            candidate_profile_result
        )
    except Exception as exc:
        message = str(exc)
        errors.append(
            HrContextBuildIssue(
                tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
                message=message,
            )
        )
        tool_results.append(
            _build_failed_tool_result(
                tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
                mode=mode,
                message=message,
            )
        )
        candidate_profile = HrCandidateProfile(
            skills=(),
            experience=(),
            seniority_signals=(),
            risks=("Candidate profile extraction failed; review candidate input manually",),
            interview_focus_areas=("Review the resume manually before interviewing",),
        )

    sources = [company_source, role_source, resume_source]
    if profile_source is not None:
        sources.append(profile_source)

    from .hr_retrieval import build_retrieval_chunks

    chunks = build_retrieval_chunks(
        company_inputs=(company_document,),
        role_description=role_document,
        sources=tuple(sources),
    )

    context = HrContext(
        schema_version=HR_CONTEXT_SCHEMA_VERSION,
        context_id=_build_input_context_id(
            mode=mode,
            company_text=company_document.markdown,
            company_uri=company_source.uri,
            role_description=normalized_role,
            resume_text=normalized_resume,
            profile_text=normalized_profile,
        ),
        fixture_id=_optional_non_empty_text(fixture_id),
        mode=mode,
        company_inputs=(company_document,),
        role_description=role_document,
        candidate_inputs=tuple(candidate_inputs),
        summaries=HrContextSummaries(
            company=company_document.summary,
            role=role_document.summary,
            candidate=_summarize_candidate_profile(candidate_profile),
        ),
        candidate_profile=candidate_profile,
        sources=tuple(sources),
        chunks=chunks,
        tool_results=tuple(tool_results),
        replay_metadata=HrReplayMetadata(transcripts=()),
    )

    return HrContextBuildResult(
        context=context,
        tool_results=tuple(tool_results),
        errors=tuple(errors),
        tool_call_events=tuple(
            tool_event_recorder.to_public_dicts() if tool_event_recorder else []
        ),
    )


def _invoke_context_langchain_tool(*, tool: Any, args: dict[str, Any], model: str | None, instruction: str) -> HrToolResult:
    from .client import build_chat_model
    from .hr_langchain_tools import build_tool_result_from_payload

    selected_args = args
    try:
        llm = build_chat_model(
            model=model,
            temperature=0,
            timeout=30,
            max_retries=1,
        ).bind_tools([tool])
        response = llm.invoke(
            [
                (
                    "system",
                    "You orchestrate HR context-building tools. If a tool is needed, call exactly one supplied tool with the provided data. Do not invent data.",
                ),
                ("human", f"{instruction}\n\nTool arguments:\n{json.dumps(args)}"),
            ]
        )
        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            first_call = tool_calls[0]
            call_args = first_call.get("args") if isinstance(first_call, dict) else None
            if isinstance(call_args, dict):
                selected_args = {**args, **call_args}
    except Exception:
        # Fall back to deterministic invocation; the tool call itself will still be recorded.
        selected_args = args

    payload = tool.invoke(selected_args)
    result = build_tool_result_from_payload(payload)
    if result is None:
        raise HrContextValidationError("LangChain HR tool returned an invalid payload")
    return result


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

    from .hr_tools import (
        candidate_profile_tool_result_to_profile,
        run_extract_candidate_profile_tool,
    )

    candidate_profile_result = run_extract_candidate_profile_tool(
        mode="mock", fixture=fixture
    )
    candidate_profile = candidate_profile_tool_result_to_profile(candidate_profile_result)

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
            candidate=_summarize_candidate_profile(candidate_profile),
        ),
        candidate_profile=candidate_profile,
        sources=sources,
        chunks=chunks,
        tool_results=(candidate_profile_result,),
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
        "candidate_profile": _candidate_profile_to_dict(context.candidate_profile),
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
    if schema_version not in SUPPORTED_HR_CONTEXT_SCHEMA_VERSIONS:
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

    summaries = _dict_to_summaries(
        _require_mapping(payload, "summaries", "HR context")
    )
    if "candidate_profile" in payload:
        candidate_profile = _dict_to_candidate_profile(
            _require_mapping(payload, "candidate_profile", "HR context")
        )
    elif schema_version == "hr-context.v1":
        candidate_profile = _legacy_candidate_profile(summaries)
    else:
        _require_mapping(payload, "candidate_profile", "HR context")

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
        summaries=summaries,
        candidate_profile=candidate_profile,
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


def _build_input_context_id(
    *,
    mode: str,
    company_text: str,
    company_uri: str,
    role_description: str,
    resume_text: str,
    profile_text: str,
) -> str:
    fingerprint_payload = {
        "schema_version": HR_CONTEXT_SCHEMA_VERSION,
        "mode": mode,
        "company_sha256": _sha256_text(company_text),
        "company_uri": company_uri,
        "role_sha256": _sha256_text(role_description),
        "resume_sha256": _sha256_text(resume_text),
        "profile_sha256": _sha256_text(profile_text),
    }
    fingerprint = json.dumps(
        fingerprint_payload, sort_keys=True, separators=(",", ":")
    )
    return f"hrctx_input_{_sha256_text(fingerprint)[:12]}"


def _build_failed_tool_result(
    *,
    tool_name: str,
    mode: str,
    message: str,
    extra: Mapping[str, Any] | None = None,
) -> HrToolResult:
    output = {"mode": mode, "error": message}
    if extra:
        output.update(extra)
    return HrToolResult(tool_name=tool_name, status="error", output=output)


def _optional_non_empty_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise HrContextValidationError("company_text and company_url must be strings")
    normalized = value.strip()
    return normalized or None


def _required_input_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HrContextValidationError(f"{field_name} is required")
    return value.strip()


def _source_uri(
    source_uris: Mapping[str, str] | None,
    key: str,
    default: str,
) -> str:
    if not source_uris or key not in source_uris:
        return default
    value = source_uris[key]
    if not isinstance(value, str) or not value.strip():
        raise HrContextValidationError(f"source_uris.{key} must be a non-empty string")
    return value.strip()


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


def _candidate_profile_to_dict(profile: HrCandidateProfile) -> dict[str, list[str]]:
    return {
        "skills": list(profile.skills),
        "experience": list(profile.experience),
        "seniority_signals": list(profile.seniority_signals),
        "risks": list(profile.risks),
        "interview_focus_areas": list(profile.interview_focus_areas),
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


def _dict_to_candidate_profile(data: Mapping[str, Any]) -> HrCandidateProfile:
    return HrCandidateProfile(
        skills=_require_str_tuple(data, "skills", "candidate_profile"),
        experience=_require_str_tuple(data, "experience", "candidate_profile"),
        seniority_signals=_require_str_tuple(
            data, "seniority_signals", "candidate_profile"
        ),
        risks=_require_str_tuple(data, "risks", "candidate_profile"),
        interview_focus_areas=_require_str_tuple(
            data, "interview_focus_areas", "candidate_profile"
        ),
    )


def _legacy_candidate_profile(summaries: HrContextSummaries) -> HrCandidateProfile:
    return HrCandidateProfile(
        skills=(),
        experience=(summaries.candidate,),
        seniority_signals=(),
        risks=(),
        interview_focus_areas=(),
    )


def _summarize_candidate_profile(profile: HrCandidateProfile) -> str:
    parts = [*profile.experience[:2], *profile.skills[:6], *profile.seniority_signals[:2]]
    if not parts:
        parts = ["Candidate profile extracted from resume and profile inputs"]
    return _truncate_text("; ".join(parts), max_chars=420)


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


def _require_str_tuple(
    data: Mapping[str, Any], key: str, parent_path: str
) -> tuple[str, ...]:
    field_path = _join_field(parent_path, key)
    values = _require_list(data, key, parent_path)
    result = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise HrContextValidationError(
                f"HR context field '{field_path}[{index}]' must be a non-empty string"
            )
        result.append(value.strip())
    return tuple(result)


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
