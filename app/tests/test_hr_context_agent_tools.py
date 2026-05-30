from __future__ import annotations

import json
import sys
import types

import pytest

import prepper_cli.client as client_module
from prepper_cli.hr_context import HrContextValidationError, _invoke_context_langchain_tool


class FakeToolMessage:
    type = "tool"

    def __init__(self, content, *, name="retrieve_company_context"):
        self.content = content
        self.name = name
        self.tool_call_id = "call_1"
        self.artifact = None


class FakeAiMessage:
    type = "ai"

    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []
        self.content = ""


class FakeTool:
    name = "retrieve_company_context"


def _install_fake_create_agent(monkeypatch, agent_response):
    captured = {}

    class FakeAgent:
        def invoke(self, payload):
            captured["invoke_payload"] = payload
            return agent_response

    def fake_create_agent(*, model, tools, system_prompt):
        captured["model"] = model
        captured["tools"] = tools
        captured["system_prompt"] = system_prompt
        return FakeAgent()

    langchain_module = types.ModuleType("langchain")
    agents_module = types.ModuleType("langchain.agents")
    agents_module.create_agent = fake_create_agent
    langchain_module.agents = agents_module
    monkeypatch.setitem(sys.modules, "langchain", langchain_module)
    monkeypatch.setitem(sys.modules, "langchain.agents", agents_module)
    monkeypatch.setattr(client_module, "build_chat_model", lambda **_kwargs: object())
    return captured


def test_invoke_context_langchain_tool_runs_real_create_agent(monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.tools import StructuredTool

    class ToolCallingFakeChatModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return self

    def retrieve_company_context(query: str):
        """Retrieve context."""
        return {
            "tool_name": "retrieve_company_context",
            "status": "success",
            "output": {"mode": "mock", "query": query},
        }

    tool = StructuredTool.from_function(
        func=retrieve_company_context,
        name="retrieve_company_context",
        description="Retrieve context.",
    )
    fake_llm = ToolCallingFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "retrieve_company_context",
                        "args": {"query": "company"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    monkeypatch.setattr(client_module, "build_chat_model", lambda **_kwargs: fake_llm)

    result = _invoke_context_langchain_tool(
        tool=tool,
        args={"query": "company"},
        model="test-model",
        instruction="Retrieve context.",
    )

    assert result.tool_name == "retrieve_company_context"
    assert result.status == "success"
    assert result.output == {"mode": "mock", "query": "company"}


def test_invoke_context_langchain_tool_uses_create_agent(monkeypatch):
    payload = {
        "tool_name": "retrieve_company_context",
        "status": "success",
        "output": {"mode": "mock", "result_count": 1},
    }
    captured = _install_fake_create_agent(
        monkeypatch,
        {
            "messages": [
                FakeAiMessage(
                    [
                        {
                            "name": "retrieve_company_context",
                            "args": {"query": "company"},
                            "id": "call_1",
                        }
                    ]
                ),
                FakeToolMessage(json.dumps(payload)),
                FakeAiMessage(),
            ]
        },
    )

    result = _invoke_context_langchain_tool(
        tool=FakeTool(),
        args={"query": "company"},
        model="test-model",
        instruction="Retrieve context.",
    )

    assert result.tool_name == "retrieve_company_context"
    assert result.status == "success"
    assert result.output == {"mode": "mock", "result_count": 1}
    assert captured["tools"][0].name == "retrieve_company_context"
    assert "Call exactly one supplied tool" in captured["system_prompt"]
    assert captured["invoke_payload"]["messages"][0]["role"] == "user"


def test_invoke_context_langchain_tool_fails_when_agent_skips_tool(monkeypatch):
    _install_fake_create_agent(monkeypatch, {"messages": [FakeAiMessage()]})

    with pytest.raises(HrContextValidationError, match="did not call expected tool"):
        _invoke_context_langchain_tool(
            tool=FakeTool(),
            args={"query": "company"},
            model=None,
            instruction="Retrieve context.",
        )


def test_invoke_context_langchain_tool_fails_on_invalid_tool_payload(monkeypatch):
    _install_fake_create_agent(
        monkeypatch,
        {"messages": [FakeAiMessage(), FakeToolMessage("not json")]},
    )

    with pytest.raises(HrContextValidationError, match="returned an invalid tool payload"):
        _invoke_context_langchain_tool(
            tool=FakeTool(),
            args={"query": "company"},
            model=None,
            instruction="Retrieve context.",
        )
