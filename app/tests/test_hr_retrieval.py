from dataclasses import replace

import pytest

from prepper_cli.hr_context import HrContextValidationError, build_mock_hr_context
from prepper_cli.hr_fixtures import validate_hr_fixture
from prepper_cli.hr_retrieval import (
    load_openrouter_embedding_config,
    retrieval_result_to_dict,
    retrieve_hr_context,
)


class FakeEmbeddings:
    def embed_query(self, query):
        assert query == "company values"
        return [1.0, 0.0]

    def embed_documents(self, documents):
        return [
            [1.0, 0.0] if "Values" in document else [0.0, 1.0]
            for document in documents
        ]


@pytest.fixture(autouse=True)
def isolated_vector_store(monkeypatch, tmp_path):
    monkeypatch.setenv("PREPPER_HR_VECTOR_STORE_DIR", str(tmp_path / "faiss"))


def test_mock_chunks_are_deterministic_with_source_metadata():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    rebuilt = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    assert context.chunks == rebuilt.chunks
    assert [chunk.id for chunk in context.chunks] == [
        "company_chunk_001",
        "role_chunk_001",
    ]
    assert "## Values" in context.chunks[0].text
    assert context.chunks[0].metadata == {
        "source_id": "company",
        "source_kind": "company",
        "source_title": "Northstar Analytics",
        "source_uri": "fixture://company.md",
        "content_sha256": context.sources[0].content_sha256,
        "start_index": "0",
        "chunk_index": "0",
    }
    assert "## Success Signals" in context.chunks[-1].text
    assert context.chunks[-1].metadata["source_uri"] == "fixture://role.md"


def test_mock_retrieval_returns_expected_chunks_and_metadata():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))

    result = retrieve_hr_context(context, query="company values", mode="mock")
    payload = retrieval_result_to_dict(result)

    assert payload["query"] == "company values"
    assert payload["mode"] == "mock"
    assert [chunk["id"] for chunk in payload["results"]] == [
        "company_chunk_001",
        "role_chunk_001",
    ]
    assert 0 < payload["results"][0]["score"] <= 1
    assert payload["results"][0]["metadata"]["source_title"] == "Northstar Analytics"
    assert payload["results"][0]["metadata"]["source_uri"] == "fixture://company.md"


def test_mock_retrieval_can_rebuild_missing_chunks_for_old_contexts():
    context = build_mock_hr_context(validate_hr_fixture("demo_hr"))
    old_context = replace(context, chunks=())

    result = retrieve_hr_context(old_context, query="company values", mode="mock")

    assert [match.chunk.id for match in result.results] == [
        "company_chunk_001",
        "role_chunk_001",
    ]


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


def test_llm_retrieval_uses_embeddings_and_source_metadata(monkeypatch):
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
    assert [chunk["id"] for chunk in payload["results"]] == ["company_chunk_001"]
    assert 0 < payload["results"][0]["score"] <= 1
    assert payload["results"][0]["metadata"]["source_uri"] == "fixture://company.md"


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
