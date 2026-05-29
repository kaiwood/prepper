from __future__ import annotations

import time
from typing import Any

from .hr_context import HrContext, HrToolResult
from .hr_retrieval import DEFAULT_MOCK_RETRIEVAL_LIMIT
from .hr_tool_events import HrToolEventRecorder, summarize_tool_result_output
from .hr_tools import (
    EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
    FETCH_COMPANY_WEBSITE_TOOL_NAME,
    FETCH_ROLE_DESCRIPTION_TOOL_NAME,
    RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
    run_extract_candidate_profile_tool,
    run_fetch_company_website_tool,
    run_fetch_role_description_tool,
    run_retrieve_company_context_tool,
)


def record_hr_tool_result(
    *,
    recorder: HrToolEventRecorder | None,
    tool_name: str,
    started_at: float,
    input_payload: dict[str, Any],
    result: HrToolResult | None = None,
    error: Exception | None = None,
) -> None:
    if recorder is None:
        return
    if error is not None:
        recorder.record(
            tool_name=tool_name,
            status="error",
            started_at=started_at,
            input_payload=input_payload,
            output_payload={"error": f"{tool_name} failed"},
        )
        return
    if result is None:
        return
    recorder.record(
        tool_name=tool_name,
        status=result.status,
        started_at=started_at,
        input_payload=input_payload,
        output_payload=summarize_tool_result_output(result.output),
    )


def create_fetch_company_website_tool(
    *,
    recorder: HrToolEventRecorder | None = None,
    allow_private_url_fetch: bool | None = None,
):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise RuntimeError("langchain-core is required for HR LangChain tools") from exc

    def fetch_company_website(url: str) -> dict[str, Any]:
        """Fetch public company website text for HR interview context building."""
        started_at = time.monotonic()
        try:
            result = run_fetch_company_website_tool(
                mode="llm",
                url=url,
                allow_private_url_fetch=allow_private_url_fetch,
            )
        except Exception as exc:
            record_hr_tool_result(
                recorder=recorder,
                tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
                started_at=started_at,
                input_payload={"url": url},
                error=exc,
            )
            raise
        record_hr_tool_result(
            recorder=recorder,
            tool_name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
            started_at=started_at,
            input_payload={"url": url},
            result=result,
        )
        return {"tool_name": result.tool_name, "status": result.status, "output": result.output}

    return StructuredTool.from_function(
        func=fetch_company_website,
        name=FETCH_COMPANY_WEBSITE_TOOL_NAME,
        description="Fetch readable public company website content from an http(s) URL.",
    )


def create_fetch_role_description_tool(
    *,
    recorder: HrToolEventRecorder | None = None,
    model: str | None = None,
    allow_private_url_fetch: bool | None = None,
):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise RuntimeError("langchain-core is required for HR LangChain tools") from exc

    def fetch_role_description(url: str) -> dict[str, Any]:
        """Fetch a public job-ad URL and extract clean role description text."""
        started_at = time.monotonic()
        try:
            result = run_fetch_role_description_tool(
                mode="llm",
                url=url,
                model=model,
                allow_private_url_fetch=allow_private_url_fetch,
            )
        except Exception as exc:
            record_hr_tool_result(
                recorder=recorder,
                tool_name=FETCH_ROLE_DESCRIPTION_TOOL_NAME,
                started_at=started_at,
                input_payload={"url": url},
                error=exc,
            )
            raise
        record_hr_tool_result(
            recorder=recorder,
            tool_name=FETCH_ROLE_DESCRIPTION_TOOL_NAME,
            started_at=started_at,
            input_payload={"url": url},
            result=result,
        )
        return {"tool_name": result.tool_name, "status": result.status, "output": result.output}

    return StructuredTool.from_function(
        func=fetch_role_description,
        name=FETCH_ROLE_DESCRIPTION_TOOL_NAME,
        description="Fetch a public job-ad URL and extract clean role description markdown.",
    )



def create_extract_candidate_profile_tool(
    *, recorder: HrToolEventRecorder | None = None, model: str | None = None
):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise RuntimeError("langchain-core is required for HR LangChain tools") from exc

    def extract_candidate_profile(resume_text: str, profile_text: str = "") -> dict[str, Any]:
        """Extract structured candidate facts, risks, and HR interview focus areas."""
        started_at = time.monotonic()
        try:
            result = run_extract_candidate_profile_tool(
                mode="llm",
                resume_text=resume_text,
                profile_text=profile_text,
                model=model,
            )
        except Exception as exc:
            record_hr_tool_result(
                recorder=recorder,
                tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
                started_at=started_at,
                input_payload={"resume_text": resume_text, "profile_text": profile_text},
                error=exc,
            )
            raise
        record_hr_tool_result(
            recorder=recorder,
            tool_name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
            started_at=started_at,
            input_payload={"resume_text": resume_text, "profile_text": profile_text},
            result=result,
        )
        return {"tool_name": result.tool_name, "status": result.status, "output": result.output}

    return StructuredTool.from_function(
        func=extract_candidate_profile,
        name=EXTRACT_CANDIDATE_PROFILE_TOOL_NAME,
        description="Extract a structured HR candidate profile from resume/profile text.",
    )


def create_retrieve_company_context_tool(
    *,
    context: HrContext,
    mode: str,
    recorder: HrToolEventRecorder | None = None,
):
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - depends on env install
        raise RuntimeError("langchain-core is required for HR LangChain tools") from exc

    def retrieve_company_context(
        query: str, limit: int = DEFAULT_MOCK_RETRIEVAL_LIMIT
    ) -> dict[str, Any]:
        """Retrieve company and role snippets relevant to an HR interview question."""
        started_at = time.monotonic()
        try:
            result = run_retrieve_company_context_tool(
                context=context,
                query=query,
                mode=mode,
                limit=limit,
            )
        except Exception as exc:
            record_hr_tool_result(
                recorder=recorder,
                tool_name=RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
                started_at=started_at,
                input_payload={"query": query, "limit": limit},
                error=exc,
            )
            raise
        record_hr_tool_result(
            recorder=recorder,
            tool_name=RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
            started_at=started_at,
            input_payload={"query": query, "limit": limit},
            result=result,
        )
        return {"tool_name": result.tool_name, "status": result.status, "output": result.output}

    return StructuredTool.from_function(
        func=retrieve_company_context,
        name=RETRIEVE_COMPANY_CONTEXT_TOOL_NAME,
        description="Retrieve relevant HR company/role context snippets by semantic query.",
    )


def build_tool_result_from_payload(payload: Any) -> HrToolResult | None:
    if not isinstance(payload, dict):
        return None
    tool_name = payload.get("tool_name")
    status = payload.get("status")
    output = payload.get("output")
    if not isinstance(tool_name, str) or not isinstance(status, str) or not isinstance(output, dict):
        return None
    return HrToolResult(tool_name=tool_name, status=status, output=output)
