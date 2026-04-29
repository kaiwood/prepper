export const DEFAULT_API_BASE_URL = "http://127.0.0.1:5000";

export const ADVANCED_SETTING_CONFIG = [
  { key: "temperature", min: 0, max: 2, step: 0.1 },
  { key: "top_p", min: 0, max: 1, step: 0.05 },
  { key: "frequency_penalty", min: -2, max: 2, step: 0.1 },
  { key: "presence_penalty", min: -2, max: 2, step: 0.1 },
];

export function resolveApiBaseUrl(rawValue) {
  if (!rawValue || rawValue === "undefined" || rawValue === "null") {
    return DEFAULT_API_BASE_URL;
  }

  return rawValue.replace(/\/$/, "");
}

export function buildApiUrl(apiBaseUrl, path) {
  return `${apiBaseUrl}${path}`;
}

export function buildAdvancedSettings(prompt) {
  return {
    temperature: prompt?.temperature ?? 0.7,
    top_p: prompt?.top_p ?? 1,
    frequency_penalty: prompt?.frequency_penalty ?? 0,
    presence_penalty: prompt?.presence_penalty ?? 0,
  };
}

export function clampAdvancedSetting(value, config) {
  return Math.min(config.max, Math.max(config.min, value));
}

export function formatAdvancedSettingValue(value, step) {
  const decimals = step < 0.1 ? 2 : 1;
  return value.toFixed(decimals);
}

export function resolveQuestionRoundtripLimit(prompt) {
  if (!prompt?.interview_rating_enabled) {
    return 5;
  }

  return typeof prompt.default_question_roundtrips === "number"
    ? prompt.default_question_roundtrips
    : 5;
}

export function resolveDifficultySelection(prompt) {
  if (!prompt?.difficulty_enabled) {
    return "medium";
  }

  return ["easy", "medium", "hard"].includes(prompt.default_difficulty)
    ? prompt.default_difficulty
    : "medium";
}

export function buildChatPayload({
  prompt,
  history,
  interviewRatingEnabled,
  interviewId,
  selectedPrompt,
  language,
  questionRoundtripLimit,
  difficultyEnabled,
  selectedDifficulty,
  selectedPromptMetadata,
  advancedSettings,
}) {
  const payload = {
    message: prompt,
    language,
  };

  if (!interviewRatingEnabled) {
    payload.conversation_history = history;
  }

  if (selectedPrompt) {
    payload.system_prompt_name = selectedPrompt;
  }

  if (interviewRatingEnabled) {
    payload.interview_id = interviewId ?? undefined;
    payload.max_question_roundtrips = questionRoundtripLimit;
  }

  if (difficultyEnabled) {
    payload.difficulty = selectedDifficulty;
  }

  if (selectedPromptMetadata) {
    payload.temperature = advancedSettings.temperature;
    payload.top_p = advancedSettings.top_p;
    payload.frequency_penalty = advancedSettings.frequency_penalty;
    payload.presence_penalty = advancedSettings.presence_penalty;
  }

  return payload;
}

export function buildStartPayload({
  selectedPrompt,
  language,
  difficultyEnabled,
  selectedDifficulty,
  selectedPromptMetadata,
  advancedSettings,
}) {
  const payload = {
    language,
  };

  if (selectedPrompt) {
    payload.system_prompt_name = selectedPrompt;
  }

  if (difficultyEnabled) {
    payload.difficulty = selectedDifficulty;
  }

  if (selectedPromptMetadata) {
    payload.temperature = advancedSettings.temperature;
    payload.top_p = advancedSettings.top_p;
    payload.frequency_penalty = advancedSettings.frequency_penalty;
    payload.presence_penalty = advancedSettings.presence_penalty;
  }

  return payload;
}
