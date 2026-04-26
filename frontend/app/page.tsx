"use client";

import { useEffect, useSyncExternalStore, useState } from "react";
import Conversation, {
  type ConversationMessage,
} from "../components/Conversation";
import MessageForm from "../components/MessageForm";
import PromptSelector from "../components/PromptSelector";
import {
  LANGUAGE_DISPLAY,
  LANGUAGE_STORAGE_KEY,
  TRANSLATIONS,
  type LanguageCode,
} from "../lib/translations";
import { hasSuspiciousPromptInjectionPattern } from "../lib/promptInjection.mjs";

type DifficultyValue = "easy" | "medium" | "hard";

type PromptMetadata = {
  id: string;
  name: string;
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  max_tokens: number;
  interview_rating_enabled?: boolean;
  default_question_roundtrips?: number;
  min_question_roundtrips?: number;
  max_question_roundtrips?: number;
  pass_threshold?: number;
  rubric_criteria?: string[];
  difficulty_enabled?: boolean;
  difficulty_levels?: DifficultyValue[];
  default_difficulty?: DifficultyValue;
};

type PromptsResponse = {
  prompts?: PromptMetadata[];
  default?: string;
  error?: string;
};

type CriterionScore = {
  criterion: string;
  score: number;
};

type InterviewRating = {
  overall_score: number;
  pass_threshold: number;
  passed: boolean;
  criterion_scores: CriterionScore[];
  strengths: string[];
  improvements: string[];
};

type InterviewStatus = {
  enabled: boolean;
  interview_complete: boolean;
  counted_question_roundtrips: number;
  question_roundtrips_limit: number;
  pass_threshold: number;
  current_turn_type: "question" | "other";
  final_result?: InterviewRating;
  metadata_warning?: boolean;
  difficulty?: DifficultyValue;
};

type ChatResponse = {
  reply?: string;
  error?: string;
  interview_enabled?: boolean;
  interview_complete?: boolean;
  counted_question_roundtrips?: number;
  question_roundtrips_limit?: number;
  pass_threshold?: number;
  current_turn_type?: "question" | "other";
  metadata_warning?: boolean;
  difficulty?: DifficultyValue;
  final_result?: InterviewRating;
};

type AdvancedSettings = {
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
};

type AdvancedSettingField = keyof AdvancedSettings;

type AdvancedSettingConfig = {
  key: AdvancedSettingField;
  min: number;
  max: number;
  step: number;
};

const DEFAULT_LANGUAGE: LanguageCode = "en";
const LANGUAGE_CHANGE_EVENT = "prepper-language-change";
const ADVANCED_SETTING_CONFIG: AdvancedSettingConfig[] = [
  { key: "temperature", min: 0, max: 2, step: 0.1 },
  { key: "top_p", min: 0, max: 1, step: 0.05 },
  { key: "frequency_penalty", min: -2, max: 2, step: 0.1 },
  { key: "presence_penalty", min: -2, max: 2, step: 0.1 },
];

function buildAdvancedSettings(prompt?: PromptMetadata): AdvancedSettings {
  return {
    temperature: prompt?.temperature ?? 0.7,
    top_p: prompt?.top_p ?? 1,
    frequency_penalty: prompt?.frequency_penalty ?? 0,
    presence_penalty: prompt?.presence_penalty ?? 0,
  };
}

function clampAdvancedSetting(
  value: number,
  config: AdvancedSettingConfig,
): number {
  return Math.min(config.max, Math.max(config.min, value));
}

function formatAdvancedSettingValue(value: number, step: number): string {
  const decimals = step < 0.1 ? 2 : 1;
  return value.toFixed(decimals);
}

function readStoredLanguage(): LanguageCode {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return storedLanguage === "en" || storedLanguage === "de"
    ? storedLanguage
    : DEFAULT_LANGUAGE;
}

function subscribeLanguageChange(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleChange = () => onStoreChange();
  window.addEventListener("storage", handleChange);
  window.addEventListener(LANGUAGE_CHANGE_EVENT, handleChange);

  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(LANGUAGE_CHANGE_EVENT, handleChange);
  };
}

export default function Home() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [availablePrompts, setAvailablePrompts] = useState<PromptMetadata[]>(
    [],
  );
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [promptsLoading, setPromptsLoading] = useState(true);
  const [promptsError, setPromptsError] = useState<string | null>(null);
  const [questionRoundtripLimit, setQuestionRoundtripLimit] = useState(5);
  const [selectedDifficulty, setSelectedDifficulty] =
    useState<DifficultyValue>("medium");
  const [interviewStatus, setInterviewStatus] =
    useState<InterviewStatus | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [advancedSettingsOpen, setAdvancedSettingsOpen] = useState(false);
  const [advancedSettings, setAdvancedSettings] = useState<AdvancedSettings>(
    buildAdvancedSettings(),
  );

  const language = useSyncExternalStore(
    subscribeLanguageChange,
    readStoredLanguage,
    () => DEFAULT_LANGUAGE,
  );
  const hasStarted = conversation.length > 0;
  const selectedPromptMetadata = availablePrompts.find(
    (prompt) => prompt.id === selectedPrompt,
  );
  const interviewRatingEnabled = Boolean(
    selectedPromptMetadata?.interview_rating_enabled,
  );
  const difficultyEnabled = Boolean(selectedPromptMetadata?.difficulty_enabled);
  const difficultyLevels = selectedPromptMetadata?.difficulty_levels ?? [
    "easy",
    "medium",
    "hard",
  ];
  const interviewCompleted = Boolean(interviewStatus?.interview_complete);
  const finalResult = interviewStatus?.final_result;
  const resultPassed = finalResult?.passed ?? false;
  const ui = TRANSLATIONS[language];
  const showInjectionWarning = hasSuspiciousPromptInjectionPattern(message);
  const difficultyLabelByValue: Record<DifficultyValue, string> = {
    easy: ui.difficultyJunior,
    medium: ui.difficultySenior,
    hard: ui.difficultyPrincipal,
  };

  const applyPromptDefaults = (
    promptId: string,
    prompts: PromptMetadata[],
    lockIfStarted: boolean,
  ) => {
    setSelectedPrompt(promptId);
    if (lockIfStarted) {
      return;
    }

    const selected = prompts.find((prompt) => prompt.id === promptId);
    setAdvancedSettings(buildAdvancedSettings(selected));

    if (!selected?.interview_rating_enabled) {
      setQuestionRoundtripLimit(5);
    } else {
      const defaultLimit = selected.default_question_roundtrips;
      setQuestionRoundtripLimit(
        typeof defaultLimit === "number" ? defaultLimit : 5,
      );
    }

    if (selected?.difficulty_enabled) {
      const defaultDifficulty = selected.default_difficulty;
      if (
        defaultDifficulty &&
        ["easy", "medium", "hard"].includes(defaultDifficulty)
      ) {
        setSelectedDifficulty(defaultDifficulty);
      } else {
        setSelectedDifficulty("medium");
      }
    } else {
      setSelectedDifficulty("medium");
    }
  };

  const handlePromptChange = (promptId: string) => {
    applyPromptDefaults(promptId, availablePrompts, hasStarted);
  };

  const updateAdvancedSetting = (
    key: AdvancedSettingField,
    rawValue: string,
  ) => {
    const config = ADVANCED_SETTING_CONFIG.find((item) => item.key === key);
    if (!config) {
      return;
    }

    const parsed = Number.parseFloat(rawValue);
    const nextValue = Number.isNaN(parsed)
      ? config.min
      : clampAdvancedSetting(parsed, config);

    setAdvancedSettings((prev) => ({ ...prev, [key]: nextValue }));
  };

  const updateLanguage = (nextLanguage: LanguageCode) => {
    if (typeof window === "undefined") {
      return;
    }

    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    window.dispatchEvent(new Event(LANGUAGE_CHANGE_EVENT));
  };

  useEffect(() => {
    let isCancelled = false;

    async function loadPrompts() {
      setPromptsLoading(true);
      setPromptsError(null);

      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/prompts`,
        );
        const data: PromptsResponse = await res.json();

        if (!res.ok) {
          if (!isCancelled) {
            setPromptsError(data.error ?? ui.errorLoadPrompts);
          }
          return;
        }

        const prompts = Array.isArray(data.prompts)
          ? data.prompts.filter(
              (p): p is PromptMetadata =>
                typeof p === "object" &&
                p !== null &&
                typeof p.id === "string" &&
                typeof p.name === "string",
            )
          : [];
        const defaultPrompt =
          typeof data.default === "string" ? data.default : "";

        if (!isCancelled) {
          setAvailablePrompts(prompts);

          if (prompts.length > 0) {
            const ids = prompts.map((p) => p.id);
            const initialPrompt = ids.includes(defaultPrompt)
              ? defaultPrompt
              : ids[0];
            applyPromptDefaults(initialPrompt, prompts, false);
          }
        }
      } catch {
        if (!isCancelled) {
          setPromptsError(ui.errorLoadPrompts);
        }
      } finally {
        if (!isCancelled) {
          setPromptsLoading(false);
        }
      }
    }

    void loadPrompts();

    return () => {
      isCancelled = true;
    };
  }, [ui.errorLoadPrompts]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!hasStarted || !message.trim() || loading || interviewCompleted) {
      return;
    }

    const prompt = message.trim();
    const history = [...conversation];
    setConversation((prev) => [...prev, { role: "user", content: prompt }]);
    setMessage("");

    setLoading(true);
    setError(null);

    try {
      const payload: {
        message: string;
        conversation_history: ConversationMessage[];
        system_prompt_name?: string;
        language: LanguageCode;
        max_question_roundtrips?: number;
        difficulty?: DifficultyValue;
        temperature?: number;
        top_p?: number;
        frequency_penalty?: number;
        presence_penalty?: number;
      } = {
        message: prompt,
        conversation_history: history,
        language,
      };

      if (selectedPrompt) {
        payload.system_prompt_name = selectedPrompt;
      }

      if (interviewRatingEnabled) {
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

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data: ChatResponse = await res.json();

      if (!res.ok) {
        setError(data.error ?? ui.errorFallback);
      } else {
        setConversation((prev) => [
          ...prev,
          { role: "assistant", content: data.reply ?? "" },
        ]);
        if (data.interview_enabled) {
          setInterviewStatus({
            enabled: true,
            interview_complete: Boolean(data.interview_complete),
            counted_question_roundtrips: data.counted_question_roundtrips ?? 0,
            question_roundtrips_limit: data.question_roundtrips_limit ?? 0,
            pass_threshold: data.pass_threshold ?? 0,
            current_turn_type: data.current_turn_type ?? "other",
            final_result: data.final_result,
            metadata_warning: data.metadata_warning,
            difficulty: data.difficulty,
          });
        } else {
          setInterviewStatus(null);
        }
      }
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }

  async function handleStart() {
    if (loading || promptsLoading || hasStarted || !selectedPrompt) {
      return;
    }

    setLoading(true);
    setError(null);
    setInterviewStatus(null);

    try {
      const payload: {
        system_prompt_name?: string;
        language: LanguageCode;
        difficulty?: DifficultyValue;
        temperature?: number;
        top_p?: number;
        frequency_penalty?: number;
        presence_penalty?: number;
      } = {
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

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/chat/start`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      const data: ChatResponse = await res.json();

      if (!res.ok) {
        setError(data.error ?? ui.errorFallback);
      } else {
        setConversation([{ role: "assistant", content: data.reply ?? "" }]);
        setInterviewStatus(null);
      }
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 gap-6">
      <div className="w-full max-w-3xl flex justify-end gap-2">
        {(Object.keys(LANGUAGE_DISPLAY) as LanguageCode[]).map((code) => {
          const isActive = code === language;
          const item = LANGUAGE_DISPLAY[code];

          return (
            <button
              key={code}
              type="button"
              onClick={() => updateLanguage(code)}
              aria-label={item.label}
              title={item.label}
              className={`rounded-md border px-2 py-1 text-sm transition-colors ${
                isActive
                  ? "border-blue-600 bg-blue-50"
                  : "border-gray-300 bg-white hover:bg-gray-50"
              }`}
            >
              {item.flag}
            </button>
          );
        })}
      </div>

      <h1 className="text-3xl font-bold mt-2">{ui.appTitle}</h1>
      <p className="text-gray-500">{ui.appSubtitle}</p>

      <PromptSelector
        prompts={availablePrompts}
        selectedPrompt={selectedPrompt}
        onPromptChange={handlePromptChange}
        loading={promptsLoading || loading}
        locked={hasStarted}
        error={promptsError}
        label={ui.promptLabel}
        loadingText={ui.promptLoading}
        unavailableText={ui.promptUnavailable}
        lockedHint={ui.promptLockedHint}
      />

      {selectedPromptMetadata && (
        <div className="w-full max-w-3xl flex flex-col">
          <div className="flex items-center justify-between gap-3">
            {interviewRatingEnabled || difficultyEnabled ? (
              <button
                type="button"
                onClick={() => setSettingsOpen((prev) => !prev)}
                className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                <span
                  className={`inline-block transition-transform duration-300 text-xs ${
                    settingsOpen ? "rotate-90" : "rotate-0"
                  }`}
                >
                  ▶
                </span>
                {ui.settingsLabel}
              </button>
            ) : (
              <div />
            )}

            <button
              type="button"
              onClick={() => setAdvancedSettingsOpen((prev) => !prev)}
              className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              <span
                className={`inline-block transition-transform duration-300 text-xs ${
                  advancedSettingsOpen ? "rotate-90" : "rotate-0"
                }`}
              >
                ▶
              </span>
              {ui.advancedSettingsLabel}
            </button>
          </div>

          {(interviewRatingEnabled || difficultyEnabled) && (
            <div
              className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
                settingsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <div className="flex flex-col gap-6 pt-4">
                  {interviewRatingEnabled && (
                    <section className="flex flex-col gap-2">
                      <label
                        htmlFor="roundtrip-limit"
                        className="text-sm font-medium text-gray-700"
                      >
                        {ui.questionLimitLabel}
                      </label>
                      <input
                        id="roundtrip-limit"
                        type="number"
                        min={
                          selectedPromptMetadata.min_question_roundtrips ?? 1
                        }
                        max={
                          selectedPromptMetadata.max_question_roundtrips ?? 10
                        }
                        value={questionRoundtripLimit}
                        disabled={hasStarted || loading}
                        onChange={(event) => {
                          const raw = Number.parseInt(event.target.value, 10);
                          const min =
                            selectedPromptMetadata.min_question_roundtrips ?? 1;
                          const max =
                            selectedPromptMetadata.max_question_roundtrips ??
                            10;
                          if (Number.isNaN(raw)) {
                            setQuestionRoundtripLimit(min);
                            return;
                          }
                          setQuestionRoundtripLimit(
                            Math.max(min, Math.min(max, raw)),
                          );
                        }}
                        className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                      />
                      <p className="text-sm text-gray-500">
                        {ui.questionLimitHint}
                      </p>
                    </section>
                  )}

                  {difficultyEnabled && (
                    <section className="flex flex-col gap-2">
                      <label
                        htmlFor="difficulty-level"
                        className="text-sm font-medium text-gray-700"
                      >
                        {ui.difficultyLabel}
                      </label>
                      <select
                        id="difficulty-level"
                        value={selectedDifficulty}
                        disabled={hasStarted || loading}
                        onChange={(event) =>
                          setSelectedDifficulty(
                            event.target.value as DifficultyValue,
                          )
                        }
                        className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                      >
                        {difficultyLevels
                          .filter((level): level is DifficultyValue =>
                            ["easy", "medium", "hard"].includes(level),
                          )
                          .map((level) => (
                            <option key={level} value={level}>
                              {difficultyLabelByValue[level]}
                            </option>
                          ))}
                      </select>
                      <p className="text-sm text-gray-500">
                        {ui.difficultyHint}
                      </p>
                    </section>
                  )}
                </div>
              </div>
            </div>
          )}

          <div
            className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
              advancedSettingsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="overflow-hidden">
              <div className="flex flex-col gap-4 pt-4">
                <p className="text-sm text-gray-500">
                  {ui.advancedSettingsHint}
                </p>
                {ADVANCED_SETTING_CONFIG.map((config) => {
                  const value = advancedSettings[config.key];
                  const labelByKey: Record<AdvancedSettingField, string> = {
                    temperature: ui.temperatureLabel,
                    top_p: ui.topPLabel,
                    frequency_penalty: ui.frequencyPenaltyLabel,
                    presence_penalty: ui.presencePenaltyLabel,
                  };

                  return (
                    <section key={config.key} className="flex flex-col gap-2">
                      <div className="flex items-center justify-between gap-3">
                        <label
                          htmlFor={`advanced-${config.key}`}
                          className="text-sm font-medium text-gray-700"
                        >
                          {labelByKey[config.key]}
                        </label>
                        <span className="text-sm tabular-nums text-gray-500">
                          {formatAdvancedSettingValue(value, config.step)}
                        </span>
                      </div>
                      <input
                        id={`advanced-${config.key}`}
                        type="range"
                        min={config.min}
                        max={config.max}
                        step={config.step}
                        value={value}
                        disabled={hasStarted || loading}
                        onChange={(event) =>
                          updateAdvancedSetting(config.key, event.target.value)
                        }
                        className="w-full accent-blue-600 disabled:accent-gray-300"
                      />
                    </section>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {interviewCompleted && interviewStatus?.final_result && (
        <section
          className={`w-full max-w-3xl rounded-xl p-4 flex flex-col gap-3 border ${
            resultPassed
              ? "border-green-200 bg-green-50 text-green-900"
              : "border-red-200 bg-red-50 text-red-900"
          }`}
        >
          <h2 className="text-xl font-semibold">{ui.interviewComplete}</h2>
          <p>
            {ui.scoreLabel}:{" "}
            {interviewStatus.final_result.overall_score.toFixed(1)} / 10
          </p>
          <p>
            {interviewStatus.final_result.passed ? ui.passLabel : ui.failLabel}
          </p>

          <div>
            <h3 className="font-medium">{ui.rubricLabel}</h3>
            <ul className="list-disc list-inside">
              {interviewStatus.final_result.criterion_scores.map(
                (criterion) => (
                  <li key={criterion.criterion}>
                    {criterion.criterion}: {criterion.score.toFixed(1)} / 10
                  </li>
                ),
              )}
            </ul>
          </div>

          <div>
            <h3 className="font-medium">{ui.strengthsLabel}</h3>
            <ul className="list-disc list-inside">
              {interviewStatus.final_result.strengths.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium">{ui.improvementsLabel}</h3>
            <ul className="list-disc list-inside">
              {interviewStatus.final_result.improvements.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <Conversation
        conversation={conversation}
        loading={loading}
        emptyStateText={ui.conversationEmpty}
        thinkingText={ui.thinking}
      />

      <MessageForm
        message={message}
        onMessageChange={setMessage}
        onSubmit={handleSubmit}
        onStart={handleStart}
        onClear={() => {
          setConversation([]);
          setMessage("");
          setError(null);
          setInterviewStatus(null);
          setAdvancedSettings(buildAdvancedSettings(selectedPromptMetadata));
          setSelectedDifficulty(
            selectedPromptMetadata?.difficulty_enabled
              ? (selectedPromptMetadata.default_difficulty ?? "medium")
              : "medium",
          );
        }}
        loading={loading}
        canClear={conversation.length > 0}
        canStart={Boolean(selectedPrompt) && availablePrompts.length > 0}
        hasStarted={hasStarted}
        disableMessaging={interviewCompleted}
        error={error}
        placeholderStarted={
          interviewCompleted
            ? ui.interviewLockedPlaceholder
            : ui.inputPlaceholderStarted
        }
        placeholderNotStarted={ui.inputPlaceholderNotStarted}
        startInterviewText={ui.startInterview}
        startingText={ui.starting}
        resetConversationText={ui.resetConversation}
        sendText={ui.send}
        thinkingText={ui.thinking}
        injectionWarningText={showInjectionWarning ? ui.injectionWarning : null}
      />
    </main>
  );
}
