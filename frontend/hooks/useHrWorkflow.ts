import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import type { ConversationMessage } from "../components/Conversation";
import type { LanguageCode } from "../lib/translations";
import { INPUT_LIMITS, formatApiError } from "../lib/inputLimits.mjs";
import { buildApiUrl } from "../lib/appLogic.mjs";
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
  buildHrInterviewStartPayload,
  buildHrInterviewTurnPayload,
} from "../lib/hrInterviewLogic.mjs";
import type {
  CandidateAnswerResponse,
  HrCompanyInputMode,
  HrCompanyFetchResponse,
  HrContextResponse,
  HrInterviewResponse,
  HrInterviewSource,
  HrLatestSetupResponse,
  HrInterviewStatus,
  HrProfileFetchResponse,
  HrProfileInputMode,
  HrResumeExtractResponse,
  HrRoleFetchResponse,
  HrResumeInputMode,
  HrRoleInputMode,
  HrSetupFormState,
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
  const [hrSetupForm, setHrSetupForm] = useState<HrSetupFormState>({
    companyUrl: "",
    companyText: "",
    roleDescription: "",
    roleUrl: "",
    resumeText: "",
    profileText: "",
  });
  const [hrCompanyInputMode, setHrCompanyInputMode] =
    useState<HrCompanyInputMode>("companyText");
  const [hrRoleInputMode, setHrRoleInputMode] =
    useState<HrRoleInputMode>("roleDescription");
  const [hrResumeInputMode, setHrResumeInputMode] =
    useState<HrResumeInputMode>("resumeText");
  const [hrProfileInputMode, setHrProfileInputMode] =
    useState<HrProfileInputMode>("profileText");
  const [hrSetupErrors, setHrSetupErrors] =
    useState<HrSetupValidationErrors>({});
  const [hrCompanyFetchLoading, setHrCompanyFetchLoading] = useState(false);
  const [hrRoleFetchLoading, setHrRoleFetchLoading] = useState(false);
  const [hrResumeExtractLoading, setHrResumeExtractLoading] = useState(false);
  const [hrProfileFetchLoading, setHrProfileFetchLoading] = useState(false);
  const [hrProfileUrl, setHrProfileUrl] = useState("");
  const [hrProfileOauthToken, setHrProfileOauthToken] = useState("");
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
  const hrHasStarted = hrConversation.length > 0;
  const latestHrInterviewerQuestion = [...hrConversation]
    .reverse()
    .find((item) => item.role === "assistant")
    ?.content.trim();

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
  }, [apiBaseUrl, enabled, ui.errorBackendUnavailable, ui.errorFallback]);

  const updateHrCompanyInputMode = (mode: HrCompanyInputMode) => {
    setHrCompanyInputMode(mode);
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm(hrSetupForm, hrSetupValidationMessages, {
        companyInputMode: mode,
        roleInputMode: hrRoleInputMode,
        resumeInputMode: hrResumeInputMode,
      });
    });
  };

  const updateHrRoleInputMode = (mode: HrRoleInputMode) => {
    setHrRoleInputMode(mode);
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm(hrSetupForm, hrSetupValidationMessages, {
        companyInputMode: hrCompanyInputMode,
        roleInputMode: mode,
        resumeInputMode: hrResumeInputMode,
      });
    });
  };

  const updateHrResumeInputMode = (mode: HrResumeInputMode) => {
    setHrResumeInputMode(mode);
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm(hrSetupForm, hrSetupValidationMessages, {
        companyInputMode: hrCompanyInputMode,
        roleInputMode: hrRoleInputMode,
        resumeInputMode: mode,
      });
    });
  };

  const updateHrProfileInputMode = (mode: HrProfileInputMode) => {
    setHrProfileInputMode(mode);
  };

  const updateHrSetupField = (
    field: keyof HrSetupFormState,
    value: string,
  ) => {
    setHrSetupForm((prev) => ({ ...prev, [field]: value }));
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm(
        { ...hrSetupForm, [field]: value },
        hrSetupValidationMessages,
        {
          companyInputMode: hrCompanyInputMode,
          roleInputMode: hrRoleInputMode,
          resumeInputMode: hrResumeInputMode,
        },
      );
    });
  };

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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/company/fetch"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_url: companyUrl }),
      });
      const data: HrCompanyFetchResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.company_text?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("companyText", data.company_text);
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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/role/fetch"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_url: roleUrl }),
      });
      const data: HrRoleFetchResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.role_description?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("roleDescription", data.role_description);
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

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(
        buildApiUrl(apiBaseUrl, "/api/hr/resume/extract"),
        {
          method: "POST",
          body: formData,
        },
      );
      const data: HrResumeExtractResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      const resumeText = data.tool_result?.output?.resume_text;
      if (typeof resumeText !== "string" || !resumeText.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("resumeText", resumeText);
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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/profile/fetch"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_url: profileUrl,
          oauth_token: oauthToken,
        }),
      });
      const data: HrProfileFetchResponse = await res.json();

      if (!res.ok) {
        setHrContextError(formatApiError(data, ui.errorFallback));
        return;
      }

      if (!data.profile_text?.trim()) {
        setHrContextError(ui.errorFallback);
        return;
      }
      updateHrSetupField("profileText", data.profile_text);
      setHrProfileInputMode("profileText");
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
      const res = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/context"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          buildHrContextPayload(hrSetupForm, {
            companyInputMode: hrCompanyInputMode,
            roleInputMode: hrRoleInputMode,
            resumeInputMode: hrResumeInputMode,
          }),
        ),
      });
      const data: HrContextResponse = await res.json();

      if (!res.ok) {
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
      const res = await fetch(
        buildApiUrl(apiBaseUrl, "/api/hr/interview/start"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            buildHrInterviewStartPayload({ contextId: hrContextId, language }),
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
      const res = await fetch(
        buildApiUrl(apiBaseUrl, "/api/presentation/candidate-answer"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_question: latestHrInterviewerQuestion,
            system_prompt_name: "hr_candidate_fit",
            language,
          }),
        },
      );
      const data: CandidateAnswerResponse = await res.json();

      if (!res.ok) {
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
    handleExtractResumePdf,
    handleFetchCompanyUrl,
    handleFetchRoleUrl,
    handleFetchSocialProfile,
    handleGenerateHrCandidateAnswer,
    handleStartHrInterview,
    handleSubmitHrInterview,
    hrCompanyFetchLoading,
    hrCompanyInputMode,
    hrContextError,
    hrContextId,
    hrContextLoading,
    hrContextResult,
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
