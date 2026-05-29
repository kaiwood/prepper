import type { LanguageCode } from "./translations";
import { buildApiUrl } from "./appLogic.mjs";
import {
  buildHrInterviewStartPayload,
  buildHrInterviewTurnPayload,
} from "./hrInterviewLogic.mjs";
import type {
  CandidateAnswerResponse,
  HrCompanyFetchResponse,
  HrContextResponse,
  HrInterviewResponse,
  HrLatestSetupResponse,
  HrProfileFetchResponse,
  HrResumeExtractResponse,
  HrRoleFetchResponse,
} from "../types/app";

type ApiResult<T> = {
  ok: boolean;
  data: T;
};

async function readJsonResponse<T>(response: Response): Promise<ApiResult<T>> {
  return {
    ok: response.ok,
    data: (await response.json()) as T,
  };
}

async function postJson<T>(
  apiBaseUrl: string,
  path: string,
  payload?: unknown,
): Promise<ApiResult<T>> {
  const response = await fetch(buildApiUrl(apiBaseUrl, path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  return readJsonResponse<T>(response);
}

export async function fetchLatestHrSetup(
  apiBaseUrl: string,
): Promise<ApiResult<HrLatestSetupResponse>> {
  const response = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/setup/latest"));
  return readJsonResponse<HrLatestSetupResponse>(response);
}

export async function clearHrSetup(apiBaseUrl: string): Promise<ApiResult<Record<string, unknown>>> {
  const response = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/setup/clear"), {
    method: "POST",
  });
  return readJsonResponse<Record<string, unknown>>(response);
}

export function fetchHrCompany(
  apiBaseUrl: string,
  companyUrl: string,
): Promise<ApiResult<HrCompanyFetchResponse>> {
  return postJson<HrCompanyFetchResponse>(apiBaseUrl, "/api/hr/company/fetch", {
    company_url: companyUrl,
  });
}

export function fetchHrRole(
  apiBaseUrl: string,
  roleUrl: string,
): Promise<ApiResult<HrRoleFetchResponse>> {
  return postJson<HrRoleFetchResponse>(apiBaseUrl, "/api/hr/role/fetch", {
    role_url: roleUrl,
  });
}

export function fetchHrProfile(
  apiBaseUrl: string,
  profileUrl: string,
  oauthToken: string,
): Promise<ApiResult<HrProfileFetchResponse>> {
  return postJson<HrProfileFetchResponse>(apiBaseUrl, "/api/hr/profile/fetch", {
    profile_url: profileUrl,
    oauth_token: oauthToken,
  });
}

export async function extractHrResume(
  apiBaseUrl: string,
  file: File,
): Promise<ApiResult<HrResumeExtractResponse>> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(buildApiUrl(apiBaseUrl, "/api/hr/resume/extract"), {
    method: "POST",
    body: formData,
  });
  return readJsonResponse<HrResumeExtractResponse>(response);
}

export function buildHrContext(
  apiBaseUrl: string,
  payload: unknown,
): Promise<ApiResult<HrContextResponse>> {
  return postJson<HrContextResponse>(apiBaseUrl, "/api/hr/context", payload);
}

export function startHrInterview(
  apiBaseUrl: string,
  contextId: string,
  language: LanguageCode,
): Promise<ApiResult<HrInterviewResponse>> {
  return postJson<HrInterviewResponse>(
    apiBaseUrl,
    "/api/hr/interview/start",
    buildHrInterviewStartPayload({ contextId, language }),
  );
}

export function continueHrInterview(
  apiBaseUrl: string,
  contextId: string,
  interviewId: string,
  message: string,
): Promise<ApiResult<HrInterviewResponse>> {
  return postJson<HrInterviewResponse>(
    apiBaseUrl,
    "/api/hr/interview",
    buildHrInterviewTurnPayload({ contextId, interviewId, message }),
  );
}

export function generateHrCandidateAnswer(
  apiBaseUrl: string,
  currentQuestion: string,
  language: LanguageCode,
): Promise<ApiResult<CandidateAnswerResponse>> {
  return postJson<CandidateAnswerResponse>(
    apiBaseUrl,
    "/api/presentation/candidate-answer",
    {
      current_question: currentQuestion,
      system_prompt_name: "hr_candidate_fit",
      language,
    },
  );
}
