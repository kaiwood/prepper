import { useEffect, useState, type FormEvent } from "react";
import type { ConversationMessage } from "../components/Conversation";
import { formatApiError } from "../lib/inputLimits.mjs";
import { hasSuspiciousPromptInjectionPattern } from "../lib/promptInjection.mjs";
import {
  ADVANCED_SETTING_CONFIG,
  buildAdvancedSettings,
  buildApiUrl,
  buildCandidateAnswerPayload,
  buildChatPayload,
  buildStartPayload,
  clampAdvancedSetting,
  resolveDifficultySelection,
  resolveQuestionRoundtripLimit,
} from "../lib/appLogic.mjs";
import type { LanguageCode } from "../lib/translations";
import type {
  AdvancedSettings,
  AdvancedSettingConfig,
  AdvancedSettingField,
  CandidateAnswerResponse,
  ChatResponse,
  DifficultyValue,
  InterviewStatus,
  PromptMetadata,
  PromptsResponse,
  TranslationStrings,
} from "../types/app";

type UseUserInterviewOptions = {
  apiBaseUrl: string;
  presentationModeEnabled: boolean;
  language: LanguageCode;
  ui: TranslationStrings;
};

export function useUserInterview({
  apiBaseUrl,
  presentationModeEnabled,
  language,
  ui,
}: UseUserInterviewOptions) {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [candidateAnswerLoading, setCandidateAnswerLoading] = useState(false);
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
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [advancedSettingsOpen, setAdvancedSettingsOpen] = useState(false);
  const [advancedSettings, setAdvancedSettings] = useState<AdvancedSettings>(
    buildAdvancedSettings(),
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
  const showInjectionWarning = hasSuspiciousPromptInjectionPattern(message);
  const latestInterviewerQuestion = [...conversation]
    .reverse()
    .find((item) => item.role === "assistant")
    ?.content.trim();
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
    setQuestionRoundtripLimit(resolveQuestionRoundtripLimit(selected));
    setSelectedDifficulty(resolveDifficultySelection(selected));
  };

  const handlePromptChange = (promptId: string) => {
    applyPromptDefaults(promptId, availablePrompts, hasStarted);
  };

  const updateAdvancedSetting = (
    key: AdvancedSettingField,
    rawValue: string,
  ) => {
    const config = (ADVANCED_SETTING_CONFIG as AdvancedSettingConfig[]).find(
      (item) => item.key === key,
    );
    if (!config) {
      return;
    }

    const parsed = Number.parseFloat(rawValue);
    const nextValue = Number.isNaN(parsed)
      ? config.min
      : clampAdvancedSetting(parsed, config);

    setAdvancedSettings((prev) => ({ ...prev, [key]: nextValue }));
  };

  useEffect(() => {
    let isCancelled = false;

    async function loadPrompts() {
      setPromptsLoading(true);
      setPromptsError(null);

      try {
        const res = await fetch(buildApiUrl(apiBaseUrl, "/api/prompts"));
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
            setSelectedPrompt(initialPrompt);
            const selected = prompts.find(
              (prompt) => prompt.id === initialPrompt,
            );
            setAdvancedSettings(buildAdvancedSettings(selected));
            setQuestionRoundtripLimit(resolveQuestionRoundtripLimit(selected));
            setSelectedDifficulty(resolveDifficultySelection(selected));
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
  }, [apiBaseUrl, ui.errorLoadPrompts]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!hasStarted || !message.trim() || loading || interviewCompleted) {
      return;
    }
    if (interviewRatingEnabled && !interviewId) {
      setError(ui.errorFallback);
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
        conversation_history?: ConversationMessage[];
        interview_id?: string;
        system_prompt_name?: string;
        language: LanguageCode;
        max_question_roundtrips?: number;
        difficulty?: DifficultyValue;
        temperature?: number;
        top_p?: number;
        frequency_penalty?: number;
        presence_penalty?: number;
      } = buildChatPayload({
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
      });

      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data: ChatResponse = await res.json();

      if (!res.ok) {
        setError(formatApiError(data, ui.errorFallback));
      } else {
        setConversation((prev) => [
          ...prev,
          { role: "assistant", content: data.reply ?? "" },
        ]);
        if (data.interview_enabled) {
          if (typeof data.interview_id === "string" && data.interview_id) {
            setInterviewId(data.interview_id);
          }
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
          setInterviewId(null);
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
    setInterviewId(null);

    try {
      const payload: {
        system_prompt_name?: string;
        language: LanguageCode;
        max_question_roundtrips?: number;
        difficulty?: DifficultyValue;
        temperature?: number;
        top_p?: number;
        frequency_penalty?: number;
        presence_penalty?: number;
      } = buildStartPayload({
        selectedPrompt,
        language,
        questionRoundtripLimit,
        difficultyEnabled,
        selectedDifficulty,
        selectedPromptMetadata,
        advancedSettings,
      });

      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/chat/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data: ChatResponse = await res.json();

      if (!res.ok) {
        setError(formatApiError(data, ui.errorFallback));
      } else {
        setConversation([{ role: "assistant", content: data.reply ?? "" }]);
        if (data.interview_enabled) {
          setInterviewId(
            typeof data.interview_id === "string" && data.interview_id
              ? data.interview_id
              : null,
          );
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
          setInterviewId(null);
          setInterviewStatus(null);
        }
      }
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateCandidateAnswer() {
    if (
      !presentationModeEnabled ||
      !hasStarted ||
      loading ||
      candidateAnswerLoading ||
      interviewCompleted ||
      !latestInterviewerQuestion
    ) {
      return;
    }

    setCandidateAnswerLoading(true);
    setError(null);

    try {
      const payload = buildCandidateAnswerPayload({
        currentQuestion: latestInterviewerQuestion,
        selectedPrompt,
        language,
        difficultyEnabled,
        selectedDifficulty,
        selectedPromptMetadata,
        advancedSettings,
      });

      const res = await fetch(
        buildApiUrl(apiBaseUrl, "/api/presentation/candidate-answer"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      const data: CandidateAnswerResponse = await res.json();

      if (!res.ok) {
        setError(formatApiError(data, ui.errorFallback));
        return;
      }

      setMessage(data.answer ?? "");
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setCandidateAnswerLoading(false);
    }
  }

  function handleClear() {
    setConversation([]);
    setMessage("");
    setError(null);
    setInterviewStatus(null);
    setInterviewId(null);
    setAdvancedSettings(buildAdvancedSettings(selectedPromptMetadata));
    setSelectedDifficulty(
      selectedPromptMetadata?.difficulty_enabled
        ? (selectedPromptMetadata.default_difficulty ?? "medium")
        : "medium",
    );
  }

  return {
    advancedSettings,
    advancedSettingsOpen,
    availablePrompts,
    candidateAnswerLoading,
    conversation,
    difficultyEnabled,
    difficultyLabelByValue,
    difficultyLevels,
    error,
    handleClear,
    handleGenerateCandidateAnswer,
    handlePromptChange,
    handleStart,
    handleSubmit,
    hasStarted,
    interviewCompleted,
    interviewRatingEnabled,
    interviewStatus,
    latestInterviewerQuestion,
    loading,
    message,
    promptsError,
    promptsLoading,
    questionRoundtripLimit,
    resultPassed,
    selectedDifficulty,
    selectedPrompt,
    selectedPromptMetadata,
    setAdvancedSettingsOpen,
    setMessage,
    setQuestionRoundtripLimit,
    setSelectedDifficulty,
    setSettingsOpen,
    settingsOpen,
    showInjectionWarning,
    updateAdvancedSetting,
  };
}

export type UserInterviewState = ReturnType<typeof useUserInterview>;
