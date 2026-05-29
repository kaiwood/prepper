export const DEFAULT_HR_INTERVIEW_MODE = "llm";

/**
 * @param {{
 *   contextId?: string,
 *   mode?: string,
 *   questionRoundtripLimit?: number,
 *   difficulty?: string,
 *   language?: string,
 *   advancedSettings?: Record<string, number>,
 *   model?: string,
 * }} [options]
 */
export function buildHrInterviewStartPayload({
  contextId,
  mode = DEFAULT_HR_INTERVIEW_MODE,
  questionRoundtripLimit,
  difficulty,
  language,
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

  const normalizedLanguage = normalizeText(language);
  if (normalizedLanguage) {
    payload.language = normalizedLanguage;
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
  const details = summarizeHrToolOutputDetails(tool?.output);

  return details.length > 0
    ? `${name}: ${status} (${details.join(", ")})`
    : `${name}: ${status}`;
}

/**
 * @param {{ name?: string, label?: string, description?: string, phase?: string }} metadata
 * @param {{ tool_name?: string, status?: string, output?: Record<string, unknown> }} [tool]
 * @param {{ status?: string, duration_ms?: number }} [event]
 * @param {string} [notUsedLabel]
 */
export function summarizeHrToolCatalogItem(metadata, tool, event, notUsedLabel = "not used") {
  const name = normalizeText(metadata?.label) || normalizeText(metadata?.name) || "tool";
  const status = normalizeText(tool?.status) || normalizeText(event?.status) || notUsedLabel;
  const details = [];
  const phase = normalizeText(metadata?.phase);
  const description = normalizeText(metadata?.description);

  if (phase) {
    details.push(`phase: ${phase}`);
  }
  details.push(...summarizeHrToolOutputDetails(tool?.output));
  if (typeof event?.duration_ms === "number" && Number.isFinite(event.duration_ms)) {
    details.push(`duration: ${event.duration_ms}ms`);
  }
  if (description) {
    details.push(description);
  }

  return details.length > 0
    ? `${name}: ${status} (${details.join(", ")})`
    : `${name}: ${status}`;
}

function summarizeHrToolOutputDetails(outputValue) {
  const output = outputValue && typeof outputValue === "object" ? outputValue : {};
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

  if (typeof output.summary === "string" && output.summary.trim()) {
    details.push(`summary: ${output.summary.trim()}`);
  }

  const sourceCount = countPublicSources(output.sources);
  if (sourceCount > 0) {
    details.push(`sources: ${sourceCount}`);
  }

  const relevanceSummary = summarizeRetrievalRelevance(output.snippets);
  if (relevanceSummary) {
    details.push(`relevance: ${relevanceSummary}`);
  }

  return details;
}

function countPublicSources(sources) {
  if (!Array.isArray(sources)) {
    return 0;
  }
  return sources.filter((source) => source && typeof source === "object").length;
}

function summarizeRetrievalRelevance(snippets) {
  if (!Array.isArray(snippets)) {
    return "";
  }

  const percentages = snippets
    .map((snippet) => {
      if (!snippet || typeof snippet !== "object") {
        return null;
      }
      const value = snippet.relevance_percent;
      if (typeof value !== "number" || !Number.isFinite(value)) {
        return null;
      }
      return Math.max(0, Math.min(100, Math.round(value)));
    })
    .filter((value) => value !== null);

  if (percentages.length === 0) {
    return "";
  }

  return percentages.map((value) => `${value}%`).join(", ");
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
