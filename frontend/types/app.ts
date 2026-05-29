import type { TRANSLATIONS, LanguageCode } from "../lib/translations";

export type DifficultyValue = "easy" | "medium" | "hard";

export type PromptMetadata = {
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

export type PromptsResponse = {
  prompts?: PromptMetadata[];
  default?: string;
  error?: string;
};

export type CriterionScore = {
  criterion: string;
  score: number;
};

export type InterviewRating = {
  overall_score: number;
  pass_threshold: number;
  passed: boolean;
  criterion_scores: CriterionScore[];
  strengths: string[];
  improvements: string[];
};

export type InterviewStatus = {
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

export type ChatResponse = {
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

export type CandidateAnswerResponse = {
  answer?: string;
  error?: string;
};

export type HrCompanyInputMode = "companyText" | "companyUrl";
export type HrRoleInputMode = "roleDescription" | "roleUrl";
export type HrResumeInputMode = "resumeText" | "resumePdf";

export type HrSetupFormState = {
  companyUrl: string;
  companyText: string;
  roleDescription: string;
  roleUrl: string;
  resumeText: string;
  profileText: string;
};

export type HrSetupValidationErrors = {
  company?: string;
  roleDescription?: string;
  resumeText?: string;
  profileText?: string;
};

export type HrContextSummaries = {
  company?: string;
  role?: string;
  candidate?: string;
};

export type HrContextSource = {
  id?: string;
  title?: string;
  uri?: string;
  kind?: string;
};

export type HrRetrievalSnippet = {
  score?: number;
  relevance_percent?: number;
  source_title?: string;
  source_uri?: string;
  text?: string;
};

export type HrCandidateProfile = {
  skills?: string[];
  experience?: string[];
  seniority_signals?: string[];
  risks?: string[];
  interview_focus_areas?: string[];
};

export type HrToolResult = {
  tool_name?: string;
  status?: string;
  output?: {
    mode?: string;
    query?: string;
    result_count?: number;
    snippets?: HrRetrievalSnippet[];
    profile?: HrCandidateProfile;
    [key: string]: unknown;
  };
};

export type HrResumeExtractResponse = {
  tool_result?: HrToolResult;
  error?: string;
};

export type HrToolCallEvent = {
  event_id?: string;
  timestamp?: string;
  flow?: string;
  sequence?: number;
  tool_name?: string;
  status?: string;
  duration_ms?: number;
};

export type HrContextError = {
  tool_name?: string;
  message?: string;
};

export type HrSetupApiFields = {
  company_url?: string;
  company_text?: string;
  role_description?: string;
  role_url?: string;
  resume_text?: string;
  profile_text?: string;
};

export type HrDemoSetupResponse = {
  setup?: HrSetupApiFields | null;
  error?: string;
};

export type HrLatestSetupResponse = {
  setup?: HrSetupApiFields | null;
  context_result?: HrContextResponse | null;
  error?: string;
};

export type HrContextResponse = {
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

export type HrInterviewSource = {
  id?: string;
  kind?: string;
  title?: string;
  url?: string;
  excerpt?: string;
  score?: number;
  relevance_percent?: number;
};

export type HrInterviewRating = {
  overall_score?: number;
  pass_threshold?: number;
  passed?: boolean;
  criterion_scores?: CriterionScore[];
  strengths?: string[];
  improvements?: string[];
};

export type HrInterviewStatus = {
  interview_complete: boolean;
  counted_question_roundtrips: number;
  question_roundtrips_limit: number;
  pass_threshold: number;
  current_turn_type: "question" | "other";
  final_result?: HrInterviewRating;
  metadata_warning?: boolean;
  difficulty?: DifficultyValue;
};

export type HrInterviewResponse = {
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

export type AdvancedSettings = {
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
};

export type AdvancedSettingField = keyof AdvancedSettings;

export type AdvancedSettingConfig = {
  key: AdvancedSettingField;
  min: number;
  max: number;
  step: number;
};

export type TranslationStrings = (typeof TRANSLATIONS)[LanguageCode];
