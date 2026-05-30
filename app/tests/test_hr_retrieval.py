import json
import logging
from dataclasses import replace

import pytest

from prepper_cli.hr_context import HrContextValidationError, build_mock_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_retrieval import (
    build_candidate_fit_retrieval_chunks,
    build_candidate_fit_retrieval_query,
    load_openrouter_embedding_config,
    retrieval_result_to_dict,
    retrieve_hr_context,
)


class FakeEmbeddings:
    def embed_query(self, query):
        assert "Company context:" in query
        assert "Role requirements:" in query
        assert "Current interview query or turn: company values" in query
        return [1.0, 0.0]

    def embed_documents(self, documents):
        return [
            [1.0, 0.0] if "# Candidate profile" in document else [0.0, 1.0]
            for document in documents
        ]


@pytest.fixture(autouse=True)
def isolated_vector_store(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_HR_VECTOR_STORE_DIR", str(tmp_path / "faiss"))


def test_mock_chunks_are_deterministic_with_source_metadata():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    rebuilt = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    assert context.chunks == rebuilt.chunks
    chunk_by_id = {chunk.id: chunk for chunk in context.chunks}
    assert {
        "company_chunk_001",
        "role_chunk_001",
        "resume_chunk_001",
        "profile_chunk_001",
        "context_metadata_chunk_001",
        "context_summaries_chunk_001",
        "candidate_profile_chunk_001",
        "context_sources_chunk_001",
        "tool_result_000_extract_candidate_profile_chunk_001",
        "replay_metadata_chunk_001",
    }.issubset(chunk_by_id)
    assert "## Values" in chunk_by_id["company_chunk_001"].text
    assert chunk_by_id["company_chunk_001"].metadata == {
        "source_id": "company",
        "source_kind": "company",
        "source_title": "Northstar Analytics",
        "source_uri": "fixture://company.md",
        "content_sha256": context.sources[0].content_sha256,
        "field_path": "company_inputs[0].markdown",
        "start_index": "0",
        "chunk_index": "0",
    }
    assert "## Success Signals" in chunk_by_id["role_chunk_001"].text
    assert chunk_by_id["role_chunk_001"].metadata["source_uri"] == "fixture://role.md"
    assert chunk_by_id["resume_chunk_001"].metadata["field_path"] == "candidate_inputs[0].markdown"
    assert chunk_by_id["candidate_profile_chunk_001"].metadata["source_kind"] == "candidate_profile"


def test_mock_retrieval_returns_expected_chunks_and_metadata():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    result = retrieve_hr_context(context, query="company values", mode="mock")
    payload = retrieval_result_to_dict(result)

    assert payload["query"] == "company values"
    assert payload["mode"] == "mock"
    assert len(payload["results"]) == 3
    assert {
        chunk["metadata"]["source_kind"] for chunk in payload["results"]
    }.issubset({"resume", "profile", "candidate_profile"})
    assert all(
        chunk["metadata"]["field_path"] in {
            "candidate_inputs[0].markdown",
            "candidate_inputs[1].markdown",
            "candidate_profile",
        }
        for chunk in payload["results"]
    )
    assert 0 < payload["results"][0]["score"] <= 1
    assert 0 < payload["results"][0]["relevance_percent"] <= 100
    candidate_result = next(
        chunk for chunk in payload["results"] if chunk["metadata"]["source_kind"] == "candidate_profile"
    )
    assert candidate_result["source"] == {
        "id": "candidate_profile",
        "kind": "candidate_profile",
        "title": "Candidate profile",
        "uri": "context://candidate_profile",
    }
    assert candidate_result["metadata"]["source_title"] == "Candidate profile"
    assert candidate_result["metadata"]["source_uri"] == "context://candidate_profile"


def test_candidate_fit_retrieval_query_uses_company_role_and_user_query():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    query = build_candidate_fit_retrieval_query(context, "company values")

    assert "Company context:" in query
    assert "Role requirements:" in query
    assert "Current interview query or turn: company values" in query
    assert "Northstar Analytics" in query
    assert "Customer Success Data Analyst" in query


def test_retrieval_logs_latency_and_counts(caplog):
    caplog.set_level(logging.INFO, logger="prepper_cli.observability")
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    retrieve_hr_context(context, query="company values", mode="mock")

    assert any(
        'event="retrieval"' in record.getMessage()
        and 'status="success"' in record.getMessage()
        and 'result_count=3' in record.getMessage()
        and 'duration_ms=' in record.getMessage()
        for record in caplog.records
    )


def test_mock_retrieval_can_rebuild_missing_chunks_for_old_contexts():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    old_context = replace(context, chunks=context.chunks[:2])

    result = retrieve_hr_context(old_context, query="company values", mode="mock")

    assert len(result.results) == 3
    assert {
        match.chunk.metadata["source_kind"] for match in result.results
    }.issubset({"resume", "profile", "candidate_profile"})
    assert any(match.chunk.metadata["field_path"] == "candidate_profile" for match in result.results)


def test_mock_retrieval_persists_faiss_index(tmp_path, monkeypatch):
    vector_store_dir = tmp_path / "stored-faiss"
    monkeypatch.setenv("PREPPER_HR_VECTOR_STORE_DIR", str(vector_store_dir))
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    first = retrieve_hr_context(context, query="company values", mode="mock")
    second = retrieve_hr_context(context, query="company values", mode="mock")

    assert [match.chunk.id for match in second.results] == [
        match.chunk.id for match in first.results
    ]
    assert list(vector_store_dir.glob("mock/*/index.faiss"))
    assert list(vector_store_dir.glob("mock/*/index.pkl"))
    manifests = list(vector_store_dir.glob("mock/*/index_manifest.json"))
    assert manifests
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["embedding_model"] == "mock-hashing-v1"
    assert manifest["vector_dimension"] == 128
    assert manifest["chunk_count"] == len(build_candidate_fit_retrieval_chunks(context))


def test_mock_retrieval_rejects_empty_query():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    with pytest.raises(HrContextValidationError, match="query"):
        retrieve_hr_context(context, query="   ", mode="mock")


def test_llm_retrieval_reports_missing_embedding_config(monkeypatch):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "")

    with pytest.raises(HrContextValidationError, match="OPENROUTER_API_KEY"):
        retrieve_hr_context(context, query="company values", mode="llm")


def test_llm_retrieval_uses_embeddings_and_source_metadata(monkeypatch, tmp_path):
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")
    monkeypatch.setattr(
        "prepper_cli.hr_retrieval._build_openrouter_embeddings",
        lambda _config: FakeEmbeddings(),
    )

    result = retrieve_hr_context(
        context,
        query="company values",
        mode="llm",
        limit=1,
    )
    payload = retrieval_result_to_dict(result)

    assert payload["mode"] == "llm"
    assert [chunk["id"] for chunk in payload["results"]] == ["candidate_profile_chunk_001"]
    assert 0 < payload["results"][0]["score"] <= 1
    assert 0 < payload["results"][0]["relevance_percent"] <= 100
    assert payload["results"][0]["source"]["uri"] == "context://candidate_profile"
    assert payload["results"][0]["metadata"]["source_uri"] == "context://candidate_profile"
    manifests = list((tmp_path / "faiss").glob("llm/*/index_manifest.json"))
    assert manifests
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["embedding_model"] == "openai/text-embedding-3-small"
    assert manifest["embedding_base_url"] == "https://openrouter.ai/api/v1"
    assert manifest["vector_dimension"] == 2


def test_openrouter_embedding_config_requires_embedding_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "")

    with pytest.raises(ValueError, match="OPENROUTER_EMBEDDING_MODEL"):
        load_openrouter_embedding_config()


def test_openrouter_embedding_config_loads_expected_names(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.example/api/v1")
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

    config = load_openrouter_embedding_config()

    assert config.api_key == "test-key"
    assert config.base_url == "https://openrouter.example/api/v1"
    assert config.embedding_model == "openai/text-embedding-3-small"
