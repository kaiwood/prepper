import { INPUT_LIMITS } from "../../lib/inputLimits.mjs";
import type { HrWorkflowState } from "../../hooks/useHrWorkflow";
import type { TranslationStrings } from "../../types/app";

type HrSetupPanelProps = {
  state: HrWorkflowState;
  ui: TranslationStrings;
  onClearAllData: () => void;
};

export default function HrSetupPanel({
  state,
  ui,
  onClearAllData,
}: HrSetupPanelProps) {
  return (
    <section className="w-full max-w-3xl rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold">{ui.hrAdminTitle}</h1>
        <p className="text-gray-500">{ui.hrAdminSubtitle}</p>
      </div>

      <form className="mt-6 flex flex-col gap-5" onSubmit={state.handleBuildHrContext}>
        <section className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50/70 p-4 shadow-sm">
          <div
            className="inline-flex w-fit rounded-lg border border-gray-200 bg-white p-1"
            role="tablist"
            aria-label={ui.hrCompanyLabel}
          >
            <button
              type="button"
              role="tab"
              aria-selected={state.hrCompanyInputMode === "companyText"}
              aria-controls="hr-company-text-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrCompanyInputMode("companyText")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrCompanyInputMode === "companyText"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrCompanyTextLabel}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={state.hrCompanyInputMode === "companyUrl"}
              aria-controls="hr-company-url-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrCompanyInputMode("companyUrl")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrCompanyInputMode === "companyUrl"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrCompanyUrlLabel}
            </button>
          </div>

          {state.hrCompanyInputMode === "companyText" ? (
            <div
              id="hr-company-text-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-company-text"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrCompanyTextLabel}
              </label>
              <textarea
                id="hr-company-text"
                value={state.hrSetupForm.companyText}
                onChange={(event) =>
                  state.updateHrSetupField("companyText", event.target.value)
                }
                disabled={state.hrContextLoading}
                maxLength={INPUT_LIMITS.companyText}
                rows={5}
                placeholder={ui.hrCompanyTextPlaceholder}
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>
          ) : (
            <div
              id="hr-company-url-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-company-url"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrCompanyUrlLabel}
              </label>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                <input
                  id="hr-company-url"
                  type="url"
                  value={state.hrSetupForm.companyUrl}
                  onChange={(event) =>
                    state.updateHrSetupField("companyUrl", event.target.value)
                  }
                  disabled={state.hrContextLoading || state.hrCompanyFetchLoading}
                  maxLength={INPUT_LIMITS.companyUrl}
                  placeholder="https://example.com/about"
                  className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <button
                  type="button"
                  onClick={state.handleFetchCompanyUrl}
                  disabled={state.hrContextLoading || state.hrCompanyFetchLoading}
                  className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:border-gray-200 disabled:text-gray-400"
                >
                  {state.hrCompanyFetchLoading ? ui.hrFetchingCompany : ui.hrFetchCompany}
                </button>
              </div>
              <p className="text-sm text-gray-500">
                {ui.hrCompanyUrlHint}
              </p>
            </div>
          )}
          {state.hrSetupErrors.company && (
            <p className="text-sm text-red-600">{state.hrSetupErrors.company}</p>
          )}
        </section>

        <section className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50/70 p-4 shadow-sm">
          <div
            className="inline-flex w-fit rounded-lg border border-gray-200 bg-white p-1"
            role="tablist"
            aria-label={ui.hrRoleLabel}
          >
            <button
              type="button"
              role="tab"
              aria-selected={state.hrRoleInputMode === "roleDescription"}
              aria-controls="hr-role-description-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrRoleInputMode("roleDescription")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrRoleInputMode === "roleDescription"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrRoleDescriptionLabel}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={state.hrRoleInputMode === "roleUrl"}
              aria-controls="hr-role-url-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrRoleInputMode("roleUrl")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrRoleInputMode === "roleUrl"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrRoleUrlLabel}
            </button>
          </div>

          {state.hrRoleInputMode === "roleDescription" ? (
            <div
              id="hr-role-description-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-role-description"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrRoleDescriptionLabel}
              </label>
              <textarea
                id="hr-role-description"
                value={state.hrSetupForm.roleDescription}
                onChange={(event) =>
                  state.updateHrSetupField("roleDescription", event.target.value)
                }
                disabled={state.hrContextLoading}
                maxLength={INPUT_LIMITS.roleDescription}
                rows={6}
                placeholder={ui.hrRoleDescriptionPlaceholder}
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>
          ) : (
            <div
              id="hr-role-url-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-role-url"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrRoleUrlLabel}
              </label>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                <input
                  id="hr-role-url"
                  type="url"
                  value={state.hrSetupForm.roleUrl}
                  onChange={(event) =>
                    state.updateHrSetupField("roleUrl", event.target.value)
                  }
                  disabled={state.hrContextLoading || state.hrRoleFetchLoading}
                  maxLength={INPUT_LIMITS.roleUrl}
                  placeholder="https://example.com/jobs/role"
                  className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <button
                  type="button"
                  onClick={state.handleFetchRoleUrl}
                  disabled={state.hrContextLoading || state.hrRoleFetchLoading}
                  className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:border-gray-200 disabled:text-gray-400"
                >
                  {state.hrRoleFetchLoading ? ui.hrFetchingRole : ui.hrFetchRole}
                </button>
              </div>
              <p className="text-sm text-gray-500">{ui.hrRoleUrlHint}</p>
            </div>
          )}
          {state.hrSetupErrors.roleDescription && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.roleDescription}
            </p>
          )}
        </section>

        <section className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50/70 p-4 shadow-sm">
          <div
            className="inline-flex w-fit rounded-lg border border-gray-200 bg-white p-1"
            role="tablist"
            aria-label={ui.hrResumeTextLabel}
          >
            <button
              type="button"
              role="tab"
              aria-selected={state.hrResumeInputMode === "resumeText"}
              aria-controls="hr-resume-text-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrResumeInputMode("resumeText")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrResumeInputMode === "resumeText"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrResumeTextLabel}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={state.hrResumeInputMode === "resumePdf"}
              aria-controls="hr-resume-pdf-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrResumeInputMode("resumePdf")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrResumeInputMode === "resumePdf"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrResumePdfLabel}
            </button>
          </div>

          {state.hrResumeInputMode === "resumeText" ? (
            <div
              id="hr-resume-text-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-resume-text"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrResumeTextLabel}
              </label>
              <textarea
                id="hr-resume-text"
                value={state.hrSetupForm.resumeText}
                onChange={(event) =>
                  state.updateHrSetupField("resumeText", event.target.value)
                }
                disabled={state.hrContextLoading}
                maxLength={INPUT_LIMITS.resumeText}
                rows={6}
                placeholder={ui.hrResumeTextPlaceholder}
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>
          ) : (
            <div
              id="hr-resume-pdf-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <span className="text-sm font-medium text-gray-700">
                {ui.hrResumePdfLabel}
              </span>
              <label
                className={`inline-flex w-fit items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  state.hrContextLoading || state.hrResumeExtractLoading
                    ? "cursor-not-allowed border-gray-200 text-gray-400"
                    : "cursor-pointer border-blue-200 text-blue-700 hover:bg-blue-50"
                }`}
              >
                {state.hrResumeExtractLoading
                  ? ui.hrExtractingResumePdf
                  : ui.hrExtractResumePdf}
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  disabled={state.hrContextLoading || state.hrResumeExtractLoading}
                  onChange={state.handleExtractResumePdf}
                  className="sr-only"
                />
              </label>
              <p className="text-sm text-gray-500">{ui.hrResumePdfHint}</p>
            </div>
          )}
          {state.hrSetupErrors.resumeText && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.resumeText}
            </p>
          )}
        </section>

        <section className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50/70 p-4 shadow-sm">
          <div
            className="inline-flex w-fit rounded-lg border border-gray-200 bg-white p-1"
            role="tablist"
            aria-label={ui.hrProfileTextLabel}
          >
            <button
              type="button"
              role="tab"
              aria-selected={state.hrProfileInputMode === "profileText"}
              aria-controls="hr-profile-text-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrProfileInputMode("profileText")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrProfileInputMode === "profileText"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrProfileTextLabel}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={state.hrProfileInputMode === "profileUrl"}
              aria-controls="hr-profile-url-panel"
              disabled={state.hrContextLoading}
              onClick={() => state.updateHrProfileInputMode("profileUrl")}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:text-gray-400 ${
                state.hrProfileInputMode === "profileUrl"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {ui.hrProfileUrlLabel}
            </button>
          </div>

          {state.hrProfileInputMode === "profileText" ? (
            <div
              id="hr-profile-text-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-profile-text"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrProfileTextLabel}
              </label>
              <textarea
                id="hr-profile-text"
                value={state.hrSetupForm.profileText}
                onChange={(event) =>
                  state.updateHrSetupField("profileText", event.target.value)
                }
                disabled={state.hrContextLoading}
                maxLength={INPUT_LIMITS.profileText}
                rows={4}
                placeholder={ui.hrProfileTextPlaceholder}
                className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              />
            </div>
          ) : (
            <div
              id="hr-profile-url-panel"
              role="tabpanel"
              className="flex flex-col gap-2"
            >
              <label
                htmlFor="hr-profile-url"
                className="text-sm font-medium text-gray-700"
              >
                {ui.hrProfileUrlLabel}
              </label>
              <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <input
                  id="hr-profile-url"
                  type="url"
                  value={state.hrProfileUrl}
                  onChange={(event) => state.setHrProfileUrl(event.target.value)}
                  disabled={state.hrContextLoading || state.hrProfileFetchLoading}
                  maxLength={INPUT_LIMITS.profileUrl}
                  placeholder={ui.hrProfileUrlPlaceholder}
                  className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <input
                  type="password"
                  value={state.hrProfileOauthToken}
                  onChange={(event) => state.setHrProfileOauthToken(event.target.value)}
                  disabled={state.hrContextLoading || state.hrProfileFetchLoading}
                  maxLength={INPUT_LIMITS.oauthToken}
                  placeholder={ui.hrProfileTokenPlaceholder}
                  aria-label={ui.hrProfileTokenLabel}
                  autoComplete="off"
                  className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <button
                  type="button"
                  onClick={state.handleFetchSocialProfile}
                  disabled={state.hrContextLoading || state.hrProfileFetchLoading}
                  className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:border-gray-200 disabled:text-gray-400"
                >
                  {state.hrProfileFetchLoading ? ui.hrFetchingProfile : ui.hrFetchProfile}
                </button>
              </div>
              <p className="text-sm text-gray-500">
                {ui.hrProfileFetchHint}
              </p>
            </div>
          )}
          {state.hrSetupErrors.profileText && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.profileText}
            </p>
          )}
        </section>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <button
            type="submit"
            disabled={state.hrContextLoading || state.hrClearLoading}
            className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-blue-300"
          >
            {state.hrContextLoading ? ui.hrBuildingContext : ui.hrBuildContext}
          </button>
          <button
            type="button"
            onClick={onClearAllData}
            disabled={
              state.hrContextLoading ||
              state.hrClearLoading ||
              state.hrCompanyFetchLoading ||
              state.hrRoleFetchLoading ||
              state.hrResumeExtractLoading ||
              state.hrProfileFetchLoading ||
              state.hrInterviewLoading ||
              state.hrCandidateAnswerLoading
            }
            className="rounded-lg bg-red-600 px-4 py-2 font-medium text-white transition-colors hover:bg-red-700 disabled:bg-red-300"
          >
            {ui.hrClearContext}
          </button>
        </div>
      </form>

      {state.hrContextError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {state.hrContextError}
        </div>
      )}

      {state.hrContextResult && (
        <section className="mt-6 flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold">{ui.hrContextSummary}</h2>
            <p className="text-sm text-gray-600">
              {ui.hrStatusLabel}: <span className="font-medium">{state.hrContextResult.status}</span>
            </p>
            {state.hrContextId ? (
              <p className="text-sm text-gray-600">
                {ui.hrContextIdLabel}: <span className="font-mono">{state.hrContextId}</span>
              </p>
            ) : (
              <p className="text-sm text-amber-700">
                {ui.hrNoContextId}
              </p>
            )}
          </div>

          {state.hrContextResult.summaries && (
            <div className="grid gap-3">
              {([
                [ui.hrCompanyLabel, state.hrContextResult.summaries.company],
                [ui.hrRoleLabel, state.hrContextResult.summaries.role],
                [ui.hrCandidateLabel, state.hrContextResult.summaries.candidate],
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

          {(state.hrContextResult.sources?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrSourcesLabel}</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.sources?.map((source, index) => (
                  <li key={`${source.id ?? source.uri ?? "source"}-${index}`}>
                    {source.title ?? source.id ?? ui.hrSourceFallback}
                    {source.uri ? ` — ${source.uri}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.tool_results?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrToolResultsLabel}</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.tool_results?.map((tool, index) => (
                  <li key={`${tool.tool_name ?? "tool"}-${index}`}>
                    {tool.tool_name ?? ui.hrToolFallback}: {tool.status ?? ui.hrUnknownStatus}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.tool_call_events?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrToolCallEventsLabel}</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.tool_call_events?.map((event, index) => (
                  <li key={`${event.event_id ?? "event"}-${index}`}>
                    #{event.sequence ?? index + 1} {event.tool_name ?? ui.hrToolFallback}: {event.status ?? ui.hrUnknownStatus}
                    {typeof event.duration_ms === "number" ? ` (${event.duration_ms}ms)` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.errors?.length ?? 0) > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <h3 className="font-medium">{ui.hrContextWarningsLabel}</h3>
              <ul className="mt-1 list-disc list-inside">
                {state.hrContextResult.errors?.map((item, index) => (
                  <li key={`${item.tool_name ?? "error"}-${index}`}>
                    {item.tool_name ? `${item.tool_name}: ` : ""}
                    {item.message ?? ui.hrUnknownError}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </section>
  );
}
