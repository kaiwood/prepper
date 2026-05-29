import test from "node:test";
import assert from "node:assert/strict";

import {
  ADVANCED_SETTING_CONFIG,
  buildAdvancedSettings,
  buildApiUrl,
  buildCandidateAnswerPayload,
  buildChatPayload,
  buildStartPayload,
  clampAdvancedSetting,
  formatAdvancedSettingValue,
  resolveApiBaseUrl,
  resolveDifficultySelection,
  resolveInitialPromptId,
  resolvePresentationMode,
  resolveQuestionRoundtripLimit,
} from "./appLogic.mjs";

const promptMetadata = {
  id: "coding_focus",
  name: "Coding Interview",
  temperature: 0.4,
  top_p: 0.95,
  frequency_penalty: 0.2,
  presence_penalty: 0.1,
  max_tokens: 1200,
  interview_rating_enabled: true,
  default_question_roundtrips: 4,
  difficulty_enabled: true,
  default_difficulty: "hard",
};

test("resolves API base URL from missing and explicit values", () => {
  assert.equal(resolveApiBaseUrl(undefined), "http://127.0.0.1:5000");
  assert.equal(resolveApiBaseUrl("null"), "http://127.0.0.1:5000");
  assert.equal(resolveApiBaseUrl("http://localhost:5000/"), "http://localhost:5000");
  assert.equal(
    buildApiUrl("http://localhost:5000", "/api/prompts"),
    "http://localhost:5000/api/prompts",
  );
});

test("resolves presentation mode from dev runner env value", () => {
  assert.equal(resolvePresentationMode("1"), true);
  assert.equal(resolvePresentationMode("true"), false);
  assert.equal(resolvePresentationMode(undefined), false);
});

test("builds advanced settings from prompt metadata and clamps inputs", () => {
  assert.deepEqual(buildAdvancedSettings(promptMetadata), {
    temperature: 0.4,
    top_p: 0.95,
    frequency_penalty: 0.2,
    presence_penalty: 0.1,
  });
  assert.deepEqual(buildAdvancedSettings(undefined), {
    temperature: 0.7,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
  });

  const temperature = ADVANCED_SETTING_CONFIG.find(
    (item) => item.key === "temperature",
  );
  assert.equal(clampAdvancedSetting(3, temperature), 2);
  assert.equal(clampAdvancedSetting(-1, temperature), 0);
  assert.equal(formatAdvancedSettingValue(0.95, 0.05), "0.95");
});

test("resolves prompt defaults for interview controls", () => {
  assert.equal(resolveQuestionRoundtripLimit(promptMetadata), 4);
  assert.equal(resolveQuestionRoundtripLimit({ interview_rating_enabled: false }), 5);
  assert.equal(resolveDifficultySelection(promptMetadata), "hard");
  assert.equal(
    resolveDifficultySelection({ difficulty_enabled: true, default_difficulty: "expert" }),
    "medium",
  );
});

test("prefers candidate fit as initial frontend prompt", () => {
  const prompts = [
    { id: "coding_focus" },
    { id: "hr_candidate_fit" },
    { id: "behavioral_focus" },
  ];

  assert.equal(
    resolveInitialPromptId(prompts, "coding_focus", "hr_candidate_fit"),
    "hr_candidate_fit",
  );
  assert.equal(
    resolveInitialPromptId(prompts, "coding_focus", "missing"),
    "coding_focus",
  );
  assert.equal(resolveInitialPromptId(prompts, "missing", "also_missing"), "coding_focus");
  assert.equal(resolveInitialPromptId([], "coding_focus", "hr_candidate_fit"), "");
});

test("builds non-interview chat payload with history", () => {
  const payload = buildChatPayload({
    prompt: "hello",
    history: [{ role: "assistant", content: "Welcome" }],
    interviewRatingEnabled: false,
    interviewId: null,
    selectedPrompt: "behavioral_focus",
    language: "de",
    questionRoundtripLimit: 4,
    difficultyEnabled: false,
    selectedDifficulty: "medium",
    selectedPromptMetadata: promptMetadata,
    advancedSettings: {
      temperature: 0.3,
      top_p: 0.9,
      frequency_penalty: 0.1,
      presence_penalty: 0,
    },
  });

  assert.deepEqual(payload, {
    message: "hello",
    language: "de",
    conversation_history: [{ role: "assistant", content: "Welcome" }],
    system_prompt_name: "behavioral_focus",
    temperature: 0.3,
    top_p: 0.9,
    frequency_penalty: 0.1,
    presence_penalty: 0,
  });
});

test("builds interview chat payload without frontend conversation history", () => {
  const payload = buildChatPayload({
    prompt: "candidate answer",
    history: [{ role: "assistant", content: "Question" }],
    interviewRatingEnabled: true,
    interviewId: "abc123",
    selectedPrompt: "coding_focus",
    language: "en",
    questionRoundtripLimit: 4,
    difficultyEnabled: true,
    selectedDifficulty: "hard",
    selectedPromptMetadata: promptMetadata,
    advancedSettings: {
      temperature: 0.4,
      top_p: 0.95,
      frequency_penalty: 0.2,
      presence_penalty: 0.1,
    },
  });

  assert.equal("conversation_history" in payload, false);
  assert.equal(payload.interview_id, "abc123");
  assert.equal(payload.max_question_roundtrips, 4);
  assert.equal(payload.difficulty, "hard");
});

test("builds start payload with prompt, difficulty, and model settings", () => {
  assert.deepEqual(
    buildStartPayload({
      selectedPrompt: "coding_focus",
      language: "en",
      questionRoundtripLimit: 4,
      difficultyEnabled: true,
      selectedDifficulty: "easy",
      selectedPromptMetadata: promptMetadata,
      advancedSettings: {
        temperature: 0.4,
        top_p: 0.95,
        frequency_penalty: 0.2,
        presence_penalty: 0.1,
      },
    }),
    {
      language: "en",
      system_prompt_name: "coding_focus",
      max_question_roundtrips: 4,
      difficulty: "easy",
      temperature: 0.4,
      top_p: 0.95,
      frequency_penalty: 0.2,
      presence_penalty: 0.1,
    },
  );
});

test("builds candidate answer payload from current interviewer question", () => {
  assert.deepEqual(
    buildCandidateAnswerPayload({
      currentQuestion: "Tell me about a production incident.",
      selectedPrompt: "behavioral_focus",
      language: "fr",
      difficultyEnabled: true,
      selectedDifficulty: "medium",
      selectedPromptMetadata: promptMetadata,
      advancedSettings: {
        temperature: 0.5,
        top_p: 0.8,
        frequency_penalty: 0,
        presence_penalty: 0.1,
      },
    }),
    {
      current_question: "Tell me about a production incident.",
      language: "fr",
      system_prompt_name: "behavioral_focus",
      difficulty: "medium",
      temperature: 0.5,
      top_p: 0.8,
      frequency_penalty: 0,
      presence_penalty: 0.1,
    },
  );
});
