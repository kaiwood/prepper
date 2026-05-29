import { useEffect, useState, type FormEvent } from "react";
import type { ConversationMessage } from "../components/Conversation";
import { formatApiError } from "../lib/inputLimits.mjs";
import { buildApiUrl } from "../lib/appLogic.mjs";
import {
  buildHrContextPayload,
  buildHrSetupFormFromApi,
  hasHrSetupValidationErrors,
  validateHrSetupForm,
} from "../lib/hrSetupLogic.mjs";
import {
  buildHrInterviewStartPayload,
  buildHrInterviewTurnPayload,
} from "../lib/hrInterviewLogic.mjs";
import type {
  HrContextResponse,
  HrDemoSetupResponse,
  HrInterviewResponse,
  HrInterviewSource,
  HrLatestSetupResponse,
  HrInterviewStatus,
  HrSetupFormState,
  HrSetupValidationErrors,
  HrToolCallEvent,
  HrToolResult,
  TranslationStrings,
} from "../types/app";

type UseHrWorkflowOptions = {
  apiBaseUrl: string;
  ui: TranslationStrings;
  enabled?: boolean;
};

export function useHrWorkflow({
  apiBaseUrl,
  ui,
  enabled = true,
}: UseHrWorkflowOptions) {
  const [hrSetupForm, setHrSetupForm] = useState<HrSetupFormState>({
    companyUrl: "",
    companyText: "",
    roleDescription: "",
    resumeText: "",
    profileText: "",
  });
  const [hrSetupErrors, setHrSetupErrors] =
    useState<HrSetupValidationErrors>({});
  const [hrDemoSetupLoading, setHrDemoSetupLoading] = useState(false);
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

  const hrInterviewCompleted = Boolean(hrInterviewStatus?.interview_complete);
  const hrFinalResult = hrInterviewStatus?.final_result;
  const hrResultPassed = hrFinalResult?.passed ?? false;
  const hrHasStarted = hrConversation.length > 0;

  useEffect(() => {
    let cancelled = false;

    async function loadLatestHrSetup() {
      try {
        const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/setup/latest"));
        const data: HrLatestSetupResponse = await res.json();
        if (cancelled) {
          return;
        }
        if (!res.ok) {
          setHrContextError(formatApiError(data, ui.errorFallback));
          return;
        }
        if (data.setup) {
          setHrSetupForm(buildHrSetupFormFromApi(data.setup));
          setHrSetupErrors({});
        }
        if (data.context_result) {
          setHrContextResult(data.context_result);
          setHrContextId(
            typeof data.context_result.context_id === "string" &&
              data.context_result.context_id
              ? data.context_result.context_id
              : null,
          );
        }
        if (data.error) {
          setHrContextError(data.error);
        }
      } catch {
        if (!cancelled) {
          setHrContextError(ui.errorBackendUnavailable);
        }
      }
    }

    if (enabled) {
      loadLatestHrSetup();
    }

    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl, enabled, ui.errorBackendUnavailable, ui.errorFallback]);

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

  async function handleLoadHrDemoSetup() {
    if (hrDemoSetupLoading || hrContextLoading) {
      return;
    }

    setHrDemoSetupLoading(true);
    setHrContextError(null);

    try {
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/setup/demo"));
      const data: HrDemoSetupResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.setup) {
        setHrContextError(ui.errorFallback);
        return;
      }

      setHrSetupForm(buildHrSetupFormFromApi(data.setup));
      setHrSetupErrors({});
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrDemoSetupLoading(false);
    }
  }

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

  async function handleBuildHrContext(e: FormEvent<HTMLFormElement>) {
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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/context"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildHrContextPayload(hrSetupForm)),
      });
      const data: HrContextResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
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
        buildApiUrl(apiBaseUrl, "/api/hr/interview/start"),
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
        setHrInterviewError(formatApiError(data, ui.errorFallback));
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

  async function handleSubmitHrInterview(e: FormEvent<HTMLFormElement>) {
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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/interview"), {
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
        setHrInterviewError(formatApiError(data, ui.errorFallback));
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

  return {
    handleBuildHrContext,
    handleLoadHrDemoSetup,
    handleStartHrInterview,
    handleSubmitHrInterview,
    hrContextError,
    hrContextId,
    hrContextLoading,
    hrContextResult,
    hrDemoSetupLoading,
    hrConversation,
    hrFinalResult,
    hrHasStarted,
    hrInterviewCompleted,
    hrInterviewError,
    hrInterviewLoading,
    hrInterviewSources,
    hrInterviewStatus,
    hrInterviewToolCallEvents,
    hrInterviewToolResults,
    hrMessage,
    hrResultPassed,
    hrSetupErrors,
    hrSetupForm,
    resetHrInterview,
    setHrMessage,
    updateHrSetupField,
  };
}

export type HrWorkflowState = ReturnType<typeof useHrWorkflow>;
