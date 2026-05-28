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
  resolvePresentationMode,
  resolveQuestionRoundtripLimit,
} from "../lib/appLogic.mjs";
import {
  buildHrContextPayload,
  hasHrSetupValidationErrors,
  validateHrSetupForm,
} from "../lib/hrSetupLogic.mjs";
import {
  buildHrInterviewStartPayload,
  buildHrInterviewTurnPayload,
  summarizeHrToolResult,
} from "../lib/hrInterviewLogic.mjs";

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
  interview_id?: string;
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

type CandidateAnswerResponse = {
  answer?: string;
  error?: string;
};

type HrSetupFormState = {
  companyUrl: string;
  companyText: string;
  roleDescription: string;
  resumeText: string;
  profileText: string;
};

type HrSetupValidationErrors = {
  company?: string;
  roleDescription?: string;
  resumeText?: string;
};

type HrContextSummaries = {
  company?: string;
  role?: string;
  candidate?: string;
};

type HrContextSource = {
  id?: string;
  title?: string;
  uri?: string;
  kind?: string;
};

type HrRetrievalSnippet = {
  score?: number;
  relevance_percent?: number;
  source_title?: string;
  source_uri?: string;
  text?: string;
};

type HrToolResult = {
  tool_name?: string;
  status?: string;
  output?: {
    mode?: string;
    query?: string;
    result_count?: number;
    snippets?: HrRetrievalSnippet[];
    [key: string]: unknown;
  };
};

type HrToolCallEvent = {
  event_id?: string;
  timestamp?: string;
  flow?: string;
  sequence?: number;
  tool_name?: string;
  status?: string;
  duration_ms?: number;
};

type HrContextError = {
  tool_name?: string;
  message?: string;
};

type HrContextResponse = {
  schema_version?: string;
  status?: string;
  context_id?: string | null;
  summaries?: HrContextSummaries | null;
  sources?: HrContextSource[];
  tool_results?: HrToolResult[];
  tool_call_events?: HrToolCallEvent[];
  errors?: HrContextError[];
  error?: string;
};

type HrInterviewSource = {
  id?: string;
  kind?: string;
  title?: string;
  url?: string;
  excerpt?: string;
  score?: number;
  relevance_percent?: number;
};

type HrInterviewRating = {
  overall_score?: number;
  pass_threshold?: number;
  passed?: boolean;
  criterion_scores?: CriterionScore[];
  strengths?: string[];
  improvements?: string[];
};

type HrInterviewStatus = {
  interview_complete: boolean;
  counted_question_roundtrips: number;
  question_roundtrips_limit: number;
  pass_threshold: number;
  current_turn_type: "question" | "other";
  final_result?: HrInterviewRating;
  metadata_warning?: boolean;
  difficulty?: DifficultyValue;
};

type HrInterviewResponse = {
  reply?: string;
  error?: string;
  interview_id?: string;
  context_id?: string;
  interview_enabled?: boolean;
  interview_complete?: boolean;
  counted_question_roundtrips?: number;
  question_roundtrips_limit?: number;
  pass_threshold?: number;
  current_turn_type?: "question" | "other";
  metadata_warning?: boolean;
  difficulty?: DifficultyValue;
  final_result?: HrInterviewRating;
  sources?: HrInterviewSource[];
  tool_results?: HrToolResult[];
  tool_call_events?: HrToolCallEvent[];
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
const API_BASE_URL = resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
const PRESENTATION_MODE_ENABLED = resolvePresentationMode(
  process.env.NEXT_PUBLIC_PREPPER_PRESENTATION_MODE,
);
const TYPED_ADVANCED_SETTING_CONFIG =
  ADVANCED_SETTING_CONFIG as AdvancedSettingConfig[];

function readStoredLanguage(): LanguageCode {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return storedLanguage === "en"
    || storedLanguage === "de"
    || storedLanguage === "fr"
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
  const [selectedArea, setSelectedArea] = useState<"user" | "admin">("user");
  const [hrSetupForm, setHrSetupForm] = useState<HrSetupFormState>({
    companyUrl: "",
    companyText: "",
    roleDescription: "",
    resumeText: "",
    profileText: "",
  });
  const [hrSetupErrors, setHrSetupErrors] =
    useState<HrSetupValidationErrors>({});
  const [hrContextResult, setHrContextResult] =
    useState<HrContextResponse | null>(null);
  const [hrContextId, setHrContextId] = useState<string | null>(null);
  const [hrContextLoading, setHrContextLoading] = useState(false);
  const [hrContextError, setHrContextError] = useState<string | null>(null);
  const [hrMessage, setHrMessage] = useState("");
  const [hrConversation, setHrConversation] = useState<ConversationMessage[]>(
    [],
  );
  const [hrInterviewId, setHrInterviewId] = useState<string | null>(null);
  const [hrInterviewStatus, setHrInterviewStatus] =
    useState<HrInterviewStatus | null>(null);
  const [hrInterviewLoading, setHrInterviewLoading] = useState(false);
  const [hrInterviewError, setHrInterviewError] = useState<string | null>(null);
  const [hrInterviewSources, setHrInterviewSources] = useState<
    HrInterviewSource[]
  >([]);
  const [hrInterviewToolResults, setHrInterviewToolResults] = useState<
    HrToolResult[]
  >([]);
  const [hrInterviewToolCallEvents, setHrInterviewToolCallEvents] = useState<
    HrToolCallEvent[]
  >([]);

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
  const hrInterviewCompleted = Boolean(hrInterviewStatus?.interview_complete);
  const hrFinalResult = hrInterviewStatus?.final_result;
  const hrResultPassed = hrFinalResult?.passed ?? false;
  const hrHasStarted = hrConversation.length > 0;
  const ui = TRANSLATIONS[language];
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
        const res = await fetch(buildApiUrl(API_BASE_URL, "/api/prompts"));
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

  const updateHrSetupField = (
    field: keyof HrSetupFormState,
    value: string,
  ) => {
    setHrSetupForm((prev) => ({ ...prev, [field]: value }));
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm({ ...hrSetupForm, [field]: value });
    });
  };

  function resetHrInterview() {
    setHrMessage("");
    setHrConversation([]);
    setHrInterviewId(null);
    setHrInterviewStatus(null);
    setHrInterviewError(null);
    setHrInterviewSources([]);
    setHrInterviewToolResults([]);
    setHrInterviewToolCallEvents([]);
  }

  function updateHrInterviewMetadata(data: HrInterviewResponse) {
    if (typeof data.interview_id === "string" && data.interview_id) {
      setHrInterviewId(data.interview_id);
    }
    setHrInterviewStatus({
      interview_complete: Boolean(data.interview_complete),
      counted_question_roundtrips: data.counted_question_roundtrips ?? 0,
      question_roundtrips_limit: data.question_roundtrips_limit ?? 0,
      pass_threshold: data.pass_threshold ?? 0,
      current_turn_type: data.current_turn_type ?? "other",
      final_result: data.final_result,
      metadata_warning: data.metadata_warning,
      difficulty: data.difficulty,
    });
    setHrInterviewSources(Array.isArray(data.sources) ? data.sources : []);
    setHrInterviewToolResults(
      Array.isArray(data.tool_results) ? data.tool_results : [],
    );
    setHrInterviewToolCallEvents(
      Array.isArray(data.tool_call_events) ? data.tool_call_events : [],
    );
  }

  async function handleBuildHrContext(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (hrContextLoading) {
      return;
    }

    const validationErrors = validateHrSetupForm(
      hrSetupForm,
    ) as HrSetupValidationErrors;
    setHrSetupErrors(validationErrors);
    if (hasHrSetupValidationErrors(validationErrors)) {
      setHrContextError(null);
      return;
    }

    setHrContextLoading(true);
    setHrContextError(null);
    setHrContextResult(null);
    setHrContextId(null);
    resetHrInterview();

    try {
      const res = await fetch(buildApiUrl(API_BASE_URL, "/api/hr/context"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildHrContextPayload(hrSetupForm)),
      });
      const data: HrContextResponse = await res.json();

      if (!res.ok) {
        setHrContextError(data.error ?? ui.errorFallback);
        return;
      }

      setHrContextResult(data);
      setHrContextId(
        typeof data.context_id === "string" && data.context_id
          ? data.context_id
          : null,
      );
      if (data.error) {
        setHrContextError(data.error);
      }
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrContextLoading(false);
    }
  }

  async function handleStartHrInterview() {
    if (!hrContextId || hrInterviewLoading || hrHasStarted) {
      return;
    }

    setHrInterviewLoading(true);
    setHrInterviewError(null);
    setHrConversation([]);
    setHrInterviewStatus(null);
    setHrInterviewId(null);
    setHrInterviewSources([]);
    setHrInterviewToolResults([]);
    setHrInterviewToolCallEvents([]);

    try {
      const res = await fetch(
        buildApiUrl(API_BASE_URL, "/api/hr/interview/start"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            buildHrInterviewStartPayload({ contextId: hrContextId }),
          ),
        },
      );
      const data: HrInterviewResponse = await res.json();

      if (!res.ok) {
        setHrInterviewError(data.error ?? ui.errorFallback);
        return;
      }

      if (typeof data.interview_id !== "string" || !data.interview_id) {
        setHrInterviewError(ui.errorFallback);
        return;
      }

      setHrConversation([{ role: "assistant", content: data.reply ?? "" }]);
      updateHrInterviewMetadata(data);
    } catch {
      setHrInterviewError(ui.errorBackendUnavailable);
    } finally {
      setHrInterviewLoading(false);
    }
  }

  async function handleSubmitHrInterview(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (
      !hrContextId ||
      !hrInterviewId ||
      !hrHasStarted ||
      !hrMessage.trim() ||
      hrInterviewLoading ||
      hrInterviewCompleted
    ) {
      return;
    }

    const prompt = hrMessage.trim();
    setHrConversation((prev) => [...prev, { role: "user", content: prompt }]);
    setHrMessage("");
    setHrInterviewLoading(true);
    setHrInterviewError(null);

    try {
      const res = await fetch(buildApiUrl(API_BASE_URL, "/api/hr/interview"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          buildHrInterviewTurnPayload({
            contextId: hrContextId,
            interviewId: hrInterviewId,
            message: prompt,
          }),
        ),
      });
      const data: HrInterviewResponse = await res.json();

      if (!res.ok) {
        setHrInterviewError(data.error ?? ui.errorFallback);
        return;
      }

      setHrConversation((prev) => [
        ...prev,
        { role: "assistant", content: data.reply ?? "" },
      ]);
      updateHrInterviewMetadata(data);
    } catch {
      setHrInterviewError(ui.errorBackendUnavailable);
    } finally {
      setHrInterviewLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
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

      const res = await fetch(buildApiUrl(API_BASE_URL, "/api/chat"), {
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

      const res = await fetch(buildApiUrl(API_BASE_URL, "/api/chat/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data: ChatResponse = await res.json();

      if (!res.ok) {
        setError(data.error ?? ui.errorFallback);
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
      !PRESENTATION_MODE_ENABLED ||
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
        buildApiUrl(API_BASE_URL, "/api/presentation/candidate-answer"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      const data: CandidateAnswerResponse = await res.json();

      if (!res.ok) {
        setError(data.error ?? ui.errorFallback);
        return;
      }

      setMessage(data.answer ?? "");
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setCandidateAnswerLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 gap-6">
      <div className="w-full max-w-3xl flex items-center justify-between gap-4">
        <nav aria-label="Area navigation" className="flex gap-2">
          {([
            ["user", "User"],
            ["admin", "Admin"],
          ] as const).map(([area, label]) => {
            const isActive = selectedArea === area;

            return (
              <button
                key={area}
                type="button"
                onClick={() => setSelectedArea(area)}
                className={`rounded-md border px-3 py-1 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                }`}
              >
                {label}
              </button>
            );
          })}
        </nav>

        <div className="flex gap-2">
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
      </div>

      {selectedArea === "admin" ? (
        <section className="w-full max-w-3xl rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl font-bold">Admin HR setup</h1>
            <p className="text-gray-500">
              Build a candidate evaluation context from company, role, resume,
              and optional profile information.
            </p>
          </div>

          <form className="mt-6 flex flex-col gap-5" onSubmit={handleBuildHrContext}>
            <section className="flex flex-col gap-2">
              <label
                htmlFor="hr-company-url"
                className="text-sm font-medium text-gray-700"
              >
                Company URL
              </label>
              <input
                id="hr-company-url"
                type="url"
                value={hrSetupForm.companyUrl}
                onChange={(event) =>
                  updateHrSetupField("companyUrl", event.target.value)
                }
                disabled={hrContextLoading}
                placeholder="https://example.com/about"
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
              <p className="text-sm text-gray-500">
                Use either a public company URL or paste company text below.
              </p>
            </section>

            <section className="flex flex-col gap-2">
              <label
                htmlFor="hr-company-text"
                className="text-sm font-medium text-gray-700"
              >
                Company text
              </label>
              <textarea
                id="hr-company-text"
                value={hrSetupForm.companyText}
                onChange={(event) =>
                  updateHrSetupField("companyText", event.target.value)
                }
                disabled={hrContextLoading}
                rows={5}
                placeholder="Paste company overview, values, and interview-relevant facts."
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
              {hrSetupErrors.company && (
                <p className="text-sm text-red-600">{hrSetupErrors.company}</p>
              )}
            </section>

            <section className="flex flex-col gap-2">
              <label
                htmlFor="hr-role-description"
                className="text-sm font-medium text-gray-700"
              >
                Role description
              </label>
              <textarea
                id="hr-role-description"
                value={hrSetupForm.roleDescription}
                onChange={(event) =>
                  updateHrSetupField("roleDescription", event.target.value)
                }
                disabled={hrContextLoading}
                rows={6}
                placeholder="Paste responsibilities, required skills, and success signals."
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
              {hrSetupErrors.roleDescription && (
                <p className="text-sm text-red-600">
                  {hrSetupErrors.roleDescription}
                </p>
              )}
            </section>

            <section className="flex flex-col gap-2">
              <label
                htmlFor="hr-resume-text"
                className="text-sm font-medium text-gray-700"
              >
                Resume text
              </label>
              <textarea
                id="hr-resume-text"
                value={hrSetupForm.resumeText}
                onChange={(event) =>
                  updateHrSetupField("resumeText", event.target.value)
                }
                disabled={hrContextLoading}
                rows={6}
                placeholder="Paste candidate resume content."
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
              {hrSetupErrors.resumeText && (
                <p className="text-sm text-red-600">
                  {hrSetupErrors.resumeText}
                </p>
              )}
            </section>

            <section className="flex flex-col gap-2">
              <label
                htmlFor="hr-profile-text"
                className="text-sm font-medium text-gray-700"
              >
                Profile text optional
              </label>
              <textarea
                id="hr-profile-text"
                value={hrSetupForm.profileText}
                onChange={(event) =>
                  updateHrSetupField("profileText", event.target.value)
                }
                disabled={hrContextLoading}
                rows={4}
                placeholder="Paste public profile or LinkedIn summary notes."
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
            </section>

            <button
              type="submit"
              disabled={hrContextLoading}
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-blue-300"
            >
              {hrContextLoading ? "Building context..." : "Build context"}
            </button>
          </form>

          {hrContextError && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {hrContextError}
            </div>
          )}

          {hrContextResult && (
            <section className="mt-6 flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex flex-col gap-1">
                <h2 className="text-xl font-semibold">Context summary</h2>
                <p className="text-sm text-gray-600">
                  Status: <span className="font-medium">{hrContextResult.status}</span>
                </p>
                {hrContextId ? (
                  <p className="text-sm text-gray-600">
                    Context ID: <span className="font-mono">{hrContextId}</span>
                  </p>
                ) : (
                  <p className="text-sm text-amber-700">
                    No context ID was returned. Review tool errors before continuing.
                  </p>
                )}
              </div>

              {hrContextResult.summaries && (
                <div className="grid gap-3">
                  {([
                    ["Company", hrContextResult.summaries.company],
                    ["Role", hrContextResult.summaries.role],
                    ["Candidate", hrContextResult.summaries.candidate],
                  ] as const).map(([label, value]) =>
                    value ? (
                      <article
                        key={label}
                        className="rounded-lg border border-gray-200 bg-white p-3"
                      >
                        <h3 className="font-medium text-gray-900">{label}</h3>
                        <p className="mt-1 text-sm text-gray-700">{value}</p>
                      </article>
                    ) : null,
                  )}
                </div>
              )}

              {(hrContextResult.sources?.length ?? 0) > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900">Sources</h3>
                  <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                    {hrContextResult.sources?.map((source, index) => (
                      <li key={`${source.id ?? source.uri ?? "source"}-${index}`}>
                        {source.title ?? source.id ?? "Source"}
                        {source.uri ? ` — ${source.uri}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(hrContextResult.tool_results?.length ?? 0) > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900">Tool results</h3>
                  <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                    {hrContextResult.tool_results?.map((tool, index) => (
                      <li key={`${tool.tool_name ?? "tool"}-${index}`}>
                        {tool.tool_name ?? "tool"}: {tool.status ?? "unknown"}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(hrContextResult.tool_call_events?.length ?? 0) > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900">Tool-call events</h3>
                  <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                    {hrContextResult.tool_call_events?.map((event, index) => (
                      <li key={`${event.event_id ?? "event"}-${index}`}>
                        #{event.sequence ?? index + 1} {event.tool_name ?? "tool"}: {event.status ?? "unknown"}
                        {typeof event.duration_ms === "number" ? ` (${event.duration_ms}ms)` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(hrContextResult.errors?.length ?? 0) > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  <h3 className="font-medium">Context build warnings</h3>
                  <ul className="mt-1 list-disc list-inside">
                    {hrContextResult.errors?.map((item, index) => (
                      <li key={`${item.tool_name ?? "error"}-${index}`}>
                        {item.tool_name ? `${item.tool_name}: ` : ""}
                        {item.message ?? "Unknown error"}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}

          {hrContextId && (
            <section className="mt-6 flex flex-col gap-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
              <div className="flex flex-col gap-1">
                <h2 className="text-xl font-semibold text-gray-900">
                  HR candidate-fit interview
                </h2>
                <p className="text-sm text-gray-600">
                  Start a live HR interview using the built company, role, and candidate context.
                </p>
                {hrInterviewStatus && (
                  <p className="text-sm text-gray-600">
                    Questions: {hrInterviewStatus.counted_question_roundtrips} / {hrInterviewStatus.question_roundtrips_limit}
                  </p>
                )}
              </div>

              {hrInterviewCompleted && hrFinalResult && (
                <section
                  className={`rounded-xl p-4 flex flex-col gap-3 border ${
                    hrResultPassed
                      ? "border-green-200 bg-green-50 text-green-900"
                      : "border-red-200 bg-red-50 text-red-900"
                  }`}
                >
                  <h3 className="text-lg font-semibold">Final score</h3>
                  <p>
                    Score: {typeof hrFinalResult.overall_score === "number"
                      ? `${hrFinalResult.overall_score.toFixed(1)} / 10`
                      : "Not available"}
                  </p>
                  {typeof hrFinalResult.passed === "boolean" && (
                    <p>{hrFinalResult.passed ? "Passed" : "Needs review"}</p>
                  )}

                  {(hrFinalResult.criterion_scores?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="font-medium">Rubric</h4>
                      <ul className="list-disc list-inside">
                        {hrFinalResult.criterion_scores?.map((criterion) => (
                          <li key={criterion.criterion}>
                            {criterion.criterion}: {criterion.score.toFixed(1)} / 10
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {(hrFinalResult.strengths?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="font-medium">Strengths</h4>
                      <ul className="list-disc list-inside">
                        {hrFinalResult.strengths?.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {(hrFinalResult.improvements?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="font-medium">Improvements</h4>
                      <ul className="list-disc list-inside">
                        {hrFinalResult.improvements?.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>
              )}

              <Conversation
                conversation={hrConversation}
                loading={hrInterviewLoading}
                emptyStateText="Start the HR interview to see candidate-fit questions."
                thinkingText="Preparing HR response..."
              />

              <MessageForm
                message={hrMessage}
                onMessageChange={setHrMessage}
                onSubmit={handleSubmitHrInterview}
                onStart={handleStartHrInterview}
                onClear={resetHrInterview}
                loading={hrInterviewLoading}
                canClear={hrConversation.length > 0}
                canStart={!hrHasStarted}
                hasStarted={hrHasStarted}
                disableMessaging={hrInterviewCompleted}
                error={hrInterviewError}
                placeholderStarted={
                  hrInterviewCompleted
                    ? "The HR interview is complete."
                    : "Type the candidate answer..."
                }
                placeholderNotStarted="Start the HR interview first."
                startInterviewText="Start HR interview"
                startingText="Starting HR interview..."
                resetConversationText="Reset HR interview"
                sendText="Send answer"
                thinkingText="Thinking..."
              />

              {(hrInterviewSources.length > 0 || hrInterviewToolResults.length > 0 || hrInterviewToolCallEvents.length > 0) && (
                <div className="grid gap-4 rounded-xl border border-blue-100 bg-white p-4">
                  {hrInterviewSources.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900">Retrieved sources</h3>
                      <ul className="mt-2 flex flex-col gap-2 text-sm text-gray-700">
                        {hrInterviewSources.map((source, index) => (
                          <li
                            key={`${source.url ?? source.title ?? "source"}-${index}`}
                            className="rounded-lg border border-gray-200 p-3"
                          >
                            <div className="font-medium text-gray-900">
                              {source.url?.startsWith("http") ? (
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-blue-700 underline"
                                >
                                  {source.title ?? source.url}
                                </a>
                              ) : (
                                source.title ?? source.url ?? "Source"
                              )}
                            </div>
                            {source.url && !source.url.startsWith("http") && (
                              <div className="text-xs text-gray-500">{source.url}</div>
                            )}
                            {source.excerpt && (
                              <p className="mt-1 text-gray-700">{source.excerpt}</p>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {hrInterviewToolResults.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900">Active tool results</h3>
                      <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                        {hrInterviewToolResults.map((tool, index) => (
                          <li key={`${tool.tool_name ?? "tool"}-${index}`}>
                            {summarizeHrToolResult(tool)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {hrInterviewToolCallEvents.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900">Tool-call events</h3>
                      <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                        {hrInterviewToolCallEvents.map((event, index) => (
                          <li key={`${event.event_id ?? "event"}-${index}`}>
                            #{event.sequence ?? index + 1} {event.tool_name ?? "tool"}: {event.status ?? "unknown"}
                            {typeof event.duration_ms === "number" ? ` (${event.duration_ms}ms)` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
        </section>
      ) : (
        <>
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
                {TYPED_ADVANCED_SETTING_CONFIG.map((config) => {
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
              setInterviewId(null);
              setAdvancedSettings(buildAdvancedSettings(selectedPromptMetadata));
              setSelectedDifficulty(
                selectedPromptMetadata?.difficulty_enabled
                  ? (selectedPromptMetadata.default_difficulty ?? "medium")
                  : "medium",
              );
            }}
            loading={loading}
            candidateAnswerLoading={candidateAnswerLoading}
            canClear={conversation.length > 0}
            canStart={Boolean(selectedPrompt) && availablePrompts.length > 0}
            hasStarted={hasStarted}
            disableMessaging={interviewCompleted}
            presentationModeEnabled={PRESENTATION_MODE_ENABLED}
            canGenerateCandidateAnswer={Boolean(latestInterviewerQuestion)}
            onGenerateCandidateAnswer={handleGenerateCandidateAnswer}
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
            generateCandidateAnswerText={ui.generateCandidateAnswer}
            generatingCandidateAnswerText={ui.generatingCandidateAnswer}
            sendText={ui.send}
            thinkingText={ui.thinking}
            injectionWarningText={
              showInjectionWarning ? ui.injectionWarning : null
            }
          />
        </>
      )}
    </main>
  );
}
