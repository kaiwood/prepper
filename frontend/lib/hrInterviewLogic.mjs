export const DEFAULT_HR_INTERVIEW_MODE = "llm";

/**
 * @param {{
 *   contextId?: string,
 *   mode?: string,
 *   questionRoundtripLimit?: number,
 *   difficulty?: string,
 *   advancedSettings?: Record<string, number>,
 *   model?: string,
 * }} [options]
 */
export function buildHrInterviewStartPayload({
  contextId,
  mode = DEFAULT_HR_INTERVIEW_MODE,
  questionRoundtripLimit,
  difficulty,
  advancedSettings,
  model,
} = {}) {
  const payload = {
    context_id: normalizeText(contextId),
    mode,
  };

  if (typeof questionRoundtripLimit === "number") {
    payload.max_question_roundtrips = questionRoundtripLimit;
  }

  const normalizedDifficulty = normalizeText(difficulty);
  if (normalizedDifficulty) {
    payload.difficulty = normalizedDifficulty;
  }

  const normalizedModel = normalizeText(model);
  if (normalizedModel) {
    payload.model = normalizedModel;
  }

  appendAdvancedSettings(payload, advancedSettings);

  return payload;
}

/**
 * @param {{ contextId?: string, interviewId?: string, message?: string }} [options]
 */
export function buildHrInterviewTurnPayload({ contextId, interviewId, message } = {}) {
  return {
    context_id: normalizeText(contextId),
    interview_id: normalizeText(interviewId),
    message: normalizeText(message),
  };
}

/**
 * @param {{ tool_name?: string, status?: string, output?: Record<string, unknown> }} tool
 */
export function summarizeHrToolResult(tool) {
  const name = normalizeText(tool?.tool_name) || "tool";
  const status = normalizeText(tool?.status) || "unknown";
  const output = tool?.output && typeof tool.output === "object" ? tool.output : {};
  const details = [];

  if (typeof output.mode === "string" && output.mode.trim()) {
    details.push(`mode: ${output.mode.trim()}`);
  }

  if (typeof output.result_count === "number") {
    details.push(`results: ${output.result_count}`);
  }

  if (typeof output.query === "string" && output.query.trim()) {
    details.push(`query: ${output.query.trim()}`);
  }

  return details.length > 0
    ? `${name}: ${status} (${details.join(", ")})`
    : `${name}: ${status}`;
}

function appendAdvancedSettings(payload, advancedSettings) {
  if (!advancedSettings || typeof advancedSettings !== "object") {
    return;
  }

  for (const key of [
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
  ]) {
    if (typeof advancedSettings[key] === "number") {
      payload[key] = advancedSettings[key];
    }
  }
}

function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}
