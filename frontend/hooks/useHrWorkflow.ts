import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useHrSetupState } from "./useHrSetupState";
import type { ConversationMessage } from "../components/Conversation";
import type { LanguageCode } from "../lib/translations";
import { INPUT_LIMITS, formatApiError } from "../lib/inputLimits.mjs";
import {
  buildHrContextPayload,
  buildHrSetupFormFromApi,
  hasHrResolvedCompanyText,
  hasHrResolvedRoleDescription,
  hasHrSetupValidationErrors,
  mergeHrResolvedSetupFields,
  validateHrSetupForm,
} from "../lib/hrSetupLogic.mjs";
import {
  buildHrContext,
  clearHrSetup,
  continueHrInterview,
  extractHrResume,
  fetchHrCompany,
  fetchHrProfile,
  fetchHrRole,
  fetchLatestHrSetup,
  generateHrCandidateAnswer,
  startHrInterview,
} from "../lib/hrWorkflowApi";
import type {
  HrCompanyInputMode,
  HrContextResponse,
  HrInterviewResponse,
  HrInterviewSource,
  HrInterviewStatus,
  HrRoleInputMode,
  HrSetupValidationErrors,
  HrToolCallEvent,
  HrToolResult,
  TranslationStrings,
} from "../types/app";

type UseHrWorkflowOptions = {
  apiBaseUrl: string;
  presentationModeEnabled: boolean;
  language: LanguageCode;
  ui: TranslationStrings;
  enabled?: boolean;
};

export function useHrWorkflow({
  apiBaseUrl,
  presentationModeEnabled,
  language,
  ui,
  enabled = true,
}: UseHrWorkflowOptions) {
  const hrSetupValidationMessages = {
    companyEither: ui.hrValidationCompanyEither,
    companyRequired: ui.hrValidationCompanyRequired,
    roleRequired: ui.hrValidationRoleRequired,
    roleEither: ui.hrValidationRoleEither,
    resumeRequired: ui.hrValidationResumeRequired,
    resumePdfRequired: ui.hrValidationResumePdfRequired,
    companyUrlLabel: ui.hrValidationCompanyUrlLabel,
    companyTextLabel: ui.hrValidationCompanyTextLabel,
    roleDescriptionLabel: ui.hrValidationRoleDescriptionLabel,
    roleUrlLabel: ui.hrValidationRoleUrlLabel,
    resumeTextLabel: ui.hrValidationResumeTextLabel,
    profileTextLabel: ui.hrValidationProfileTextLabel,
    tooLong: ui.hrValidationTooLong,
  };
  const {
    hrCompanyInputMode,
    hrProfileInputMode,
    hrProfileOauthToken,
    hrProfileUrl,
    hrResumeInputMode,
    hrRoleInputMode,
    hrSetupErrors,
    hrSetupForm,
    resetHrSetupState,
    setHrCompanyInputMode,
    setHrProfileOauthToken,
    setHrProfileUrl,
    setHrRoleInputMode,
    setHrSetupErrors,
    setHrSetupForm,
    updateHrCompanyInputMode,
    updateHrProfileInputMode,
    updateHrResumeInputMode,
    updateHrRoleInputMode,
    updateHrSetupField,
  } = useHrSetupState(hrSetupValidationMessages);
  const [hrCompanyFetchLoading, setHrCompanyFetchLoading] = useState(false);
  const [hrRoleFetchLoading, setHrRoleFetchLoading] = useState(false);
  const [hrResumeExtractLoading, setHrResumeExtractLoading] = useState(false);
  const [hrProfileFetchLoading, setHrProfileFetchLoading] = useState(false);
  const [hrContextResult, setHrContextResult] =
    useState<HrContextResponse | null>(null);
  const [hrSetupToolResults, setHrSetupToolResults] = useState<
    HrToolResult[]
  >([]);
  const [hrContextId, setHrContextId] = useState<string | null>(null);
  const [hrContextLoading, setHrContextLoading] = useState(false);
  const [hrClearLoading, setHrClearLoading] = useState(false);
  const [hrContextError, setHrContextError] = useState<string | null>(null);
  const [hrMessage, setHrMessage] = useState("");
  const [hrConversation, setHrConversation] = useState<ConversationMessage[]>(
    [],
  );
  const [hrInterviewId, setHrInterviewId] = useState<string | null>(null);
  const [hrInterviewStatus, setHrInterviewStatus] =
    useState<HrInterviewStatus | null>(null);
  const [hrInterviewLoading, setHrInterviewLoading] = useState(false);
  const [hrCandidateAnswerLoading, setHrCandidateAnswerLoading] =
    useState(false);
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
  const latestHrInterviewerQuestion = [...hrConversation]
    .reverse()
    .find((item) => item.role === "assistant")
    ?.content.trim();

  useEffect(() => {
    let cancelled = false;

    async function loadLatestHrSetup() {
      try {
        const { ok, data } = await fetchLatestHrSetup(apiBaseUrl);
        if (cancelled) {
          return;
        }
        if (!ok) {
          setHrContextError(formatApiError(data, ui.errorFallback));
          return;
        }
        if (data.setup) {
          const restoredForm = mergeHrResolvedSetupFields(
            buildHrSetupFormFromApi(data.setup),
            data.context_result,
          );
          setHrSetupForm(restoredForm);
          setHrCompanyInputMode(
            hasHrResolvedCompanyText(data.context_result)
              ? "companyText"
              : getCompanyInputModeFromSetup(data.setup),
          );
          setHrRoleInputMode(
            hasHrResolvedRoleDescription(data.context_result)
              ? "roleDescription"
              : getRoleInputModeFromSetup(data.setup),
          );
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
  }, [
    apiBaseUrl,
    enabled,
    setHrCompanyInputMode,
    setHrRoleInputMode,
    setHrSetupErrors,
    setHrSetupForm,
    ui.errorBackendUnavailable,
    ui.errorFallback,
  ]);

  async function handleFetchCompanyUrl() {
    if (hrCompanyFetchLoading || hrContextLoading) {
      return;
    }

    const companyUrl = hrSetupForm.companyUrl.trim();
    if (!companyUrl) {
      setHrContextError(`${ui.hrCompanyUrlLabel} is required.`);
      return;
    }
    if (companyUrl.length > INPUT_LIMITS.companyUrl) {
      setHrContextError(`${ui.hrCompanyUrlLabel} is too long.`);
      return;
    }

    setHrCompanyFetchLoading(true);
    setHrContextError(null);

    try {
      const { ok, data } = await fetchHrCompany(apiBaseUrl, companyUrl);

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.company_text?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("companyText", data.company_text);
      setHrSetupToolResults((prev) => upsertHrToolResult(prev, data.tool_result));
      setHrCompanyInputMode("companyText");
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrCompanyFetchLoading(false);
    }
  }

  async function handleFetchRoleUrl() {
    if (hrRoleFetchLoading || hrContextLoading) {
      return;
    }

    const roleUrl = hrSetupForm.roleUrl.trim();
    if (!roleUrl) {
      setHrContextError(`${ui.hrRoleUrlLabel} is required.`);
      return;
    }
    if (roleUrl.length > INPUT_LIMITS.roleUrl) {
      setHrContextError(`${ui.hrRoleUrlLabel} is too long.`);
      return;
    }

    setHrRoleFetchLoading(true);
    setHrContextError(null);

    try {
      const { ok, data } = await fetchHrRole(apiBaseUrl, roleUrl);

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.role_description?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("roleDescription", data.role_description);
      setHrSetupToolResults((prev) => upsertHrToolResult(prev, data.tool_result));
      setHrRoleInputMode("roleDescription");
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrRoleFetchLoading(false);
    }
  }

  async function handleExtractResumePdf(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || hrResumeExtractLoading || hrContextLoading) {
      return;
    }

    setHrResumeExtractLoading(true);
    setHrContextError(null);

    try {
      const { ok, data } = await extractHrResume(apiBaseUrl, file);

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      const resumeText = data.tool_result?.output?.resume_text;
      if (typeof resumeText !== "string" || !resumeText.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("resumeText", resumeText);
      setHrSetupToolResults((prev) =>
        upsertHrToolResult(prev, aliasHrToolResult(data.tool_result, "extract_resume_pdf_profile")),
      );
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrResumeExtractLoading(false);
    }
  }

  async function handleFetchSocialProfile() {
    if (hrProfileFetchLoading || hrContextLoading) {
      return;
    }

    const profileUrl = hrProfileUrl.trim();
    const oauthToken = hrProfileOauthToken.trim();
    if (!profileUrl) {
      setHrContextError(`${ui.hrProfileUrlLabel} is required.`);
      return;
    }
    if (!oauthToken) {
      setHrContextError(`${ui.hrProfileTokenLabel} is required.`);
      return;
    }
    if (profileUrl.length > INPUT_LIMITS.profileUrl) {
      setHrContextError(`${ui.hrProfileUrlLabel} is too long.`);
      return;
    }
    if (oauthToken.length > INPUT_LIMITS.oauthToken) {
      setHrContextError(`${ui.hrProfileTokenLabel} is too long.`);
      return;
    }

    setHrProfileFetchLoading(true);
    setHrContextError(null);

    try {
      const { ok, data } = await fetchHrProfile(
        apiBaseUrl,
        profileUrl,
        oauthToken,
      );

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.profile_text?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("profileText", data.profile_text);
      setHrSetupToolResults((prev) => upsertHrToolResult(prev, data.tool_result));
      updateHrProfileInputMode("profileText");
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrProfileOauthToken("");
      setHrProfileFetchLoading(false);
    }
  }


  function resetHrInterview() {
    setHrMessage("");
    setHrConversation([]);
    setHrInterviewId(null);
    setHrInterviewStatus(null);
    setHrCandidateAnswerLoading(false);
    setHrInterviewError(null);
    setHrInterviewSources([]);
    setHrInterviewToolResults([]);
    setHrInterviewToolCallEvents([]);
  }

  function clearLocalHrData() {
    resetHrSetupState();
    setHrContextResult(null);
    setHrSetupToolResults([]);
    setHrContextId(null);
    setHrContextError(null);
    resetHrInterview();
  }

  async function handleClearAllData() {
    if (
      hrClearLoading ||
      hrContextLoading ||
      hrCompanyFetchLoading ||
      hrRoleFetchLoading ||
      hrResumeExtractLoading ||
      hrProfileFetchLoading ||
      hrInterviewLoading ||
      hrCandidateAnswerLoading
    ) {
      return;
    }

    setHrClearLoading(true);
    setHrContextError(null);

    try {
      const { ok, data } = await clearHrSetup(apiBaseUrl);

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      clearLocalHrData();
    } catch {
      setHrContextError(ui.errorBackendUnavailable);
    } finally {
      setHrClearLoading(false);
    }
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
      hrSetupValidationMessages,
      {
        companyInputMode: hrCompanyInputMode,
        roleInputMode: hrRoleInputMode,
        resumeInputMode: hrResumeInputMode,
      },
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
      const { ok, data } = await buildHrContext(
        apiBaseUrl,
        buildHrContextPayload(hrSetupForm, {
          companyInputMode: hrCompanyInputMode,
          roleInputMode: hrRoleInputMode,
          resumeInputMode: hrResumeInputMode,
        }),
      );

      if (!ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      setHrSetupForm((prev) => mergeHrResolvedSetupFields(prev, data));
      if (hasHrResolvedCompanyText(data)) {
        setHrCompanyInputMode("companyText");
      }
      if (hasHrResolvedRoleDescription(data)) {
        setHrRoleInputMode("roleDescription");
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
      const { ok, data } = await startHrInterview(
        apiBaseUrl,
        hrContextId,
        language,
      );

      if (!ok) {
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
      const { ok, data } = await continueHrInterview(
        apiBaseUrl,
        hrContextId,
        hrInterviewId,
        prompt,
      );

      if (!ok) {
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

  async function handleGenerateHrCandidateAnswer() {
    if (
      !presentationModeEnabled ||
      !hrHasStarted ||
      hrInterviewLoading ||
      hrCandidateAnswerLoading ||
      hrInterviewCompleted ||
      !latestHrInterviewerQuestion
    ) {
      return;
    }

    setHrCandidateAnswerLoading(true);
    setHrInterviewError(null);

    try {
      const { ok, data } = await generateHrCandidateAnswer(
        apiBaseUrl,
        latestHrInterviewerQuestion,
        language,
      );

      if (!ok) {
        setHrInterviewError(formatApiError(data, ui.errorFallback));
        return;
      }

      setHrMessage(data.answer ?? "");
    } catch {
      setHrInterviewError(ui.errorBackendUnavailable);
    } finally {
      setHrCandidateAnswerLoading(false);
    }
  }

  return {
    handleBuildHrContext,
    handleClearAllData,
    handleExtractResumePdf,
    handleFetchCompanyUrl,
    handleFetchRoleUrl,
    handleFetchSocialProfile,
    handleGenerateHrCandidateAnswer,
    handleStartHrInterview,
    handleSubmitHrInterview,
    hrCompanyFetchLoading,
    hrCompanyInputMode,
    hrClearLoading,
    hrContextError,
    hrContextId,
    hrContextLoading,
    hrContextResult,
    hrSetupToolResults,
    hrCandidateAnswerLoading,
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
    hrProfileFetchLoading,
    hrProfileInputMode,
    hrProfileOauthToken,
    hrProfileUrl,
    hrResumeExtractLoading,
    hrResumeInputMode,
    hrRoleFetchLoading,
    hrRoleInputMode,
    latestHrInterviewerQuestion,
    hrSetupErrors,
    hrSetupForm,
    resetHrInterview,
    setHrMessage,
    setHrProfileOauthToken,
    setHrProfileUrl,
    updateHrCompanyInputMode,
    updateHrProfileInputMode,
    updateHrResumeInputMode,
    updateHrRoleInputMode,
    updateHrSetupField,
  };
}

function upsertHrToolResult(
  results: HrToolResult[],
  toolResult?: HrToolResult,
): HrToolResult[] {
  if (!toolResult?.tool_name) {
    return results;
  }
  return [
    ...results.filter((item) => item.tool_name !== toolResult.tool_name),
    toolResult,
  ];
}

function aliasHrToolResult(
  toolResult: HrToolResult | undefined,
  toolName: string,
): HrToolResult | undefined {
  if (!toolResult) {
    return undefined;
  }
  return { ...toolResult, tool_name: toolName };
}

function getCompanyInputModeFromSetup(setup: {
  company_text?: unknown;
  company_url?: unknown;
}): HrCompanyInputMode {
  if (typeof setup.company_text === "string" && setup.company_text.trim()) {
    return "companyText";
  }
  if (typeof setup.company_url === "string" && setup.company_url.trim()) {
    return "companyUrl";
  }
  return "companyText";
}

function getRoleInputModeFromSetup(setup: {
  role_description?: unknown;
  role_url?: unknown;
}): HrRoleInputMode {
  if (typeof setup.role_url === "string" && setup.role_url.trim()) {
    return "roleUrl";
  }
  return "roleDescription";
}

export type HrWorkflowState = ReturnType<typeof useHrWorkflow>;
