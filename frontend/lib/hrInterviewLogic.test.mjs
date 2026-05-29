import test from "node:test";
import assert from "node:assert/strict";

import {
  buildHrInterviewStartPayload,
  buildHrInterviewTurnPayload,
  summarizeHrToolCatalogItem,
  summarizeHrToolResult,
} from "./hrInterviewLogic.mjs";

test("builds HR interview start payload with live mode by default", () => {
  assert.deepEqual(
    buildHrInterviewStartPayload({
      contextId: " hrctx_123 ",
      questionRoundtripLimit: 3,
      difficulty: " medium ",
      language: " de ",
      advancedSettings: {
        temperature: 0.4,
        top_p: 0.9,
        frequency_penalty: 0.1,
        presence_penalty: 0,
      },
    }),
    {
      context_id: "hrctx_123",
      mode: "llm",
      max_question_roundtrips: 3,
      difficulty: "medium",
      language: "de",
      temperature: 0.4,
      top_p: 0.9,
      frequency_penalty: 0.1,
      presence_penalty: 0,
    },
  );
});

test("builds HR interview start payload with explicit mock mode", () => {
  assert.deepEqual(
    buildHrInterviewStartPayload({ contextId: "hrctx_123", mode: "mock" }),
    {
      context_id: "hrctx_123",
      mode: "mock",
    },
  );
});

test("builds HR interview turn payload", () => {
  assert.deepEqual(
    buildHrInterviewTurnPayload({
      contextId: " hrctx_123 ",
      interviewId: " interview_456 ",
      message: " Candidate answer. ",
    }),
    {
      context_id: "hrctx_123",
      interview_id: "interview_456",
      message: "Candidate answer.",
    },
  );
});

test("summarizes HR tool catalog item details", () => {
  assert.equal(
    summarizeHrToolCatalogItem(
      {
        name: "fetch_company_website",
        label: "Fetch company website",
        phase: "context",
        description: "Fetch readable public company website content.",
      },
      {
        tool_name: "fetch_company_website",
        status: "success",
        output: {
          mode: "llm",
          sources: [{ uri: "https://example.com" }],
        },
      },
      { status: "success", duration_ms: 42 },
      "not used",
    ),
    "Fetch company website: success (phase: context, mode: llm, sources: 1, duration: 42ms, Fetch readable public company website content.)",
  );
});

test("summarizes unused HR tool catalog item", () => {
  assert.equal(
    summarizeHrToolCatalogItem(
      {
        name: "retrieve_company_context",
        label: "Retrieve company context",
        phase: "interview",
      },
      undefined,
      undefined,
      "not used",
    ),
    "Retrieve company context: not used (phase: interview)",
  );
});

test("summarizes HR tool result details", () => {
  assert.equal(
    summarizeHrToolResult({
      tool_name: "retrieve_company_context",
      status: "success",
      output: {
        mode: "llm",
        result_count: 2,
        query: "company values",
        snippets: [{ relevance_percent: 84 }, { relevance_percent: 41 }],
      },
    }),
    "retrieve_company_context: success (mode: llm, results: 2, query: company values, relevance: 84%, 41%)",
  );
});
