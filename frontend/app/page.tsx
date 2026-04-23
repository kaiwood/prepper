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
  is_completed: boolean;
  counted_question_roundtrips: number;
  question_roundtrips_limit: number;
  pass_threshold: number;
  current_turn_type: "question" | "other";
  rating?: InterviewRating;
};

type ChatResponse = {
  reply?: string;
  error?: string;
  interview_status?: InterviewStatus;
};

const DEFAULT_LANGUAGE: LanguageCode = "en";
const LANGUAGE_CHANGE_EVENT = "prepper-language-change";

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
  const interviewCompleted = Boolean(interviewStatus?.is_completed);
  const ui = TRANSLATIONS[language];
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
        setInterviewStatus(data.interview_status ?? null);
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
      } = {
        language,
      };

      if (selectedPrompt) {
        payload.system_prompt_name = selectedPrompt;
      }

      if (difficultyEnabled) {
        payload.difficulty = selectedDifficulty;
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

      {(interviewRatingEnabled || difficultyEnabled) && (
        <div className="w-full max-w-3xl flex flex-col">
          <button
            type="button"
            onClick={() => setSettingsOpen((prev) => !prev)}
            className="flex items-center gap-1.5 self-start text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            <span
              className={`inline-block transition-transform duration-300 text-xs ${
                settingsOpen ? "rotate-90" : "rotate-0"
              }`}
            >
              ▶
            </span>
            Settings
          </button>
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
                      min={selectedPromptMetadata?.min_question_roundtrips ?? 1}
                      max={
                        selectedPromptMetadata?.max_question_roundtrips ?? 10
                      }
                      value={questionRoundtripLimit}
                      disabled={hasStarted || loading}
                      onChange={(event) => {
                        const raw = Number.parseInt(event.target.value, 10);
                        const min =
                          selectedPromptMetadata?.min_question_roundtrips ?? 1;
                        const max =
                          selectedPromptMetadata?.max_question_roundtrips ?? 10;
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
                    <p className="text-sm text-gray-500">{ui.difficultyHint}</p>
                  </section>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {interviewCompleted && interviewStatus?.rating && (
        <section className="w-full max-w-3xl rounded-xl border border-green-200 bg-green-50 p-4 flex flex-col gap-3">
          <h2 className="text-xl font-semibold text-green-900">
            {ui.interviewComplete}
          </h2>
          <p className="text-green-900">
            {ui.scoreLabel}: {interviewStatus.rating.overall_score.toFixed(1)} /
            10
          </p>
          <p className="text-green-900">
            {interviewStatus.rating.passed ? ui.passLabel : ui.failLabel}
          </p>

          <div>
            <h3 className="font-medium text-green-900">{ui.rubricLabel}</h3>
            <ul className="list-disc list-inside text-green-900">
              {interviewStatus.rating.criterion_scores.map((criterion) => (
                <li key={criterion.criterion}>
                  {criterion.criterion}: {criterion.score.toFixed(1)} / 10
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-green-900">{ui.strengthsLabel}</h3>
            <ul className="list-disc list-inside text-green-900">
              {interviewStatus.rating.strengths.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-green-900">
              {ui.improvementsLabel}
            </h3>
            <ul className="list-disc list-inside text-green-900">
              {interviewStatus.rating.improvements.map((item) => (
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
      />
    </main>
  );
}
