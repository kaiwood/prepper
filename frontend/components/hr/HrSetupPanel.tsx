import { useState } from "react";
import { INPUT_LIMITS } from "../../lib/inputLimits.mjs";
import type { HrWorkflowState } from "../../hooks/useHrWorkflow";
import type { TranslationStrings } from "../../types/app";

type HrSetupPanelProps = {
  state: HrWorkflowState;
  ui: TranslationStrings;
  onClearAllData: () => void;
};

type SetupSection = "company" | "role" | "resume" | "profile";

const cardBase =
  "cursor-pointer rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-colors hover:border-blue-200";
const inputBase =
  "rounded-lg border border-slate-200 bg-white px-3 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400";
const textareaBase = `${inputBase} min-h-40 font-mono text-sm`;
const primaryButton =
  "rounded-lg bg-blue-600 px-5 py-3 font-medium text-white shadow-md transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300";
const secondaryButton =
  "rounded-lg border border-blue-200 bg-white px-4 py-3 text-sm font-medium text-blue-700 shadow-sm transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400";

export default function HrSetupPanel({
  state,
  ui,
  onClearAllData,
}: HrSetupPanelProps) {
  const [activeSection, setActiveSection] = useState<SetupSection | null>(null);
  const [resumeModalOpen, setResumeModalOpen] = useState(false);

  if (activeSection) {
    return (
      <section className="mx-auto w-full max-w-[980px]">
        <button
          type="button"
          onClick={() => setActiveSection(null)}
          className="mb-4 text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          ‹ {ui.hrBackToOverview}
        </button>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {activeSection === "company" && <CompanyDetail state={state} ui={ui} />}
          {activeSection === "role" && <RoleDetail state={state} ui={ui} />}
          {activeSection === "resume" && (
            <ResumeDetail
              state={state}
              ui={ui}
              onOpenUpload={() => setResumeModalOpen(true)}
            />
          )}
          {activeSection === "profile" && <ProfileDetail state={state} ui={ui} />}
        </div>

        {state.hrContextError && (
          <ErrorBox message={state.hrContextError} />
        )}
        {resumeModalOpen && (
          <ResumeUploadModal
            state={state}
            ui={ui}
            onClose={() => setResumeModalOpen(false)}
          />
        )}
      </section>
    );
  }

  const cards = [
    {
      section: "company" as const,
      icon: "▥",
      title: ui.hrCompanyLabel,
      description: ui.hrSetupCompanyDescription,
      action: state.hrSetupForm.companyText || state.hrSetupForm.companyUrl ? ui.hrEditCompany : ui.hrAddCompany,
      complete: Boolean(state.hrSetupForm.companyText || state.hrSetupForm.companyUrl),
    },
    {
      section: "role" as const,
      icon: "▣",
      title: ui.hrRoleLabel,
      description: ui.hrSetupRoleDescription,
      action: state.hrSetupForm.roleDescription || state.hrSetupForm.roleUrl ? ui.hrEditRole : ui.hrAddRole,
      complete: Boolean(state.hrSetupForm.roleDescription || state.hrSetupForm.roleUrl),
    },
    {
      section: "resume" as const,
      icon: "▤",
      title: ui.hrResumeLabel,
      description: ui.hrSetupResumeDescription,
      action: state.hrSetupForm.resumeText ? ui.hrEditResume : ui.hrAddResume,
      complete: Boolean(state.hrSetupForm.resumeText),
    },
    {
      section: "profile" as const,
      icon: "♙",
      title: ui.hrProfileLabel,
      description: ui.hrSetupProfileDescription,
      action: state.hrSetupForm.profileText ? ui.hrEditProfile : ui.hrAddProfile,
      complete: Boolean(state.hrSetupForm.profileText),
      optional: true,
    },
  ];

  return (
    <section className="mx-auto w-full max-w-[1180px] rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-slate-950">{ui.hrAdminTitle}</h1>
        <p className="text-sm text-slate-500">{ui.hrAdminSubtitle}</p>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <button
            key={card.section}
            type="button"
            onClick={() => setActiveSection(card.section)}
            className={`${cardBase} text-left`}
          >
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-2xl text-blue-600">
              {card.icon}
            </div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-slate-950">{card.title}</h2>
              {card.optional && <span className="text-sm text-slate-500">({ui.hrOptionalLabel})</span>}
              {card.complete && <span className="ml-auto text-green-600">✓</span>}
            </div>
            <p className="mt-3 min-h-12 text-sm leading-6 text-slate-500">
              {card.description}
            </p>
            <div className="mt-6 rounded-lg border border-blue-100 px-4 py-3 text-center text-sm font-medium text-blue-700">
              {card.action}
            </div>
          </button>
        ))}
      </div>

      <form className="mt-7" onSubmit={state.handleBuildHrContext}>
        <div className="flex flex-col gap-4 rounded-xl border border-blue-100 bg-blue-50/60 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-blue-200 bg-white text-blue-600">
              ✧
            </div>
            <span>
              {ui.hrSetupCompleteHint}
            </span>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClearAllData}
              disabled={isBusy(state)}
              className="rounded-lg border border-slate-200 bg-white px-5 py-3 font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {ui.hrClearContext}
            </button>
            <button
              type="submit"
              disabled={state.hrContextLoading || state.hrClearLoading}
              className={primaryButton}
            >
              {state.hrContextLoading ? ui.hrBuildingContext : ui.hrCreateContext}
            </button>
          </div>
        </div>
      </form>

      <ValidationSummary state={state} />
      {state.hrContextError && <ErrorBox message={state.hrContextError} />}
      {state.hrContextResult && <ContextStatus state={state} ui={ui} />}
    </section>
  );
}

function CompanyDetail({
  state,
  ui,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
}) {
  return (
    <DetailFrame
      title={ui.hrCompanyInfoTitle}
      subtitle={ui.hrCompanyInfoSubtitle}
      tabs={[
        {
          id: "companyText",
          label: ui.hrCompanyTextLabel,
          active: state.hrCompanyInputMode === "companyText",
          onClick: () => state.updateHrCompanyInputMode("companyText"),
        },
        {
          id: "companyUrl",
          label: ui.hrCompanyUrlLabel,
          active: state.hrCompanyInputMode === "companyUrl",
          onClick: () => state.updateHrCompanyInputMode("companyUrl"),
        },
      ]}
    >
      {state.hrCompanyInputMode === "companyText" ? (
        <Field label={`${ui.hrCompanyTextLabel} (${ui.hrMarkdownSupportedSuffix})`} htmlFor="hr-company-text">
          <textarea
            id="hr-company-text"
            value={state.hrSetupForm.companyText}
            onChange={(event) => state.updateHrSetupField("companyText", event.target.value)}
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.companyText}
            rows={8}
            placeholder={ui.hrCompanyTextPlaceholder}
            className={textareaBase}
          />
        </Field>
      ) : (
        <div className="grid gap-4">
          <Field label={ui.hrCompanyUrlLabel} htmlFor="hr-company-url">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <input
                id="hr-company-url"
                type="url"
                value={state.hrSetupForm.companyUrl}
                onChange={(event) => state.updateHrSetupField("companyUrl", event.target.value)}
                disabled={state.hrContextLoading || state.hrCompanyFetchLoading}
                maxLength={INPUT_LIMITS.companyUrl}
                placeholder={ui.hrCompanyUrlPlaceholder}
                className={inputBase}
              />
              <button
                type="button"
                onClick={state.handleFetchCompanyUrl}
                disabled={state.hrContextLoading || state.hrCompanyFetchLoading}
                className={secondaryButton}
              >
                {state.hrCompanyFetchLoading ? ui.hrFetchingCompany : ui.hrFetchCompany}
              </button>
            </div>
          </Field>
          <InfoBox>{ui.hrCompanyUrlHint}</InfoBox>
        </div>
      )}
      {state.hrSetupErrors.company && <InlineError message={state.hrSetupErrors.company} />}
    </DetailFrame>
  );
}

function RoleDetail({
  state,
  ui,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
}) {
  return (
    <DetailFrame
      title={ui.hrRoleInfoTitle}
      subtitle={ui.hrRoleInfoSubtitle}
      tabs={[
        {
          id: "roleDescription",
          label: ui.hrRoleDescriptionLabel,
          active: state.hrRoleInputMode === "roleDescription",
          onClick: () => state.updateHrRoleInputMode("roleDescription"),
        },
        {
          id: "roleUrl",
          label: ui.hrRoleUrlLabel,
          active: state.hrRoleInputMode === "roleUrl",
          onClick: () => state.updateHrRoleInputMode("roleUrl"),
        },
      ]}
    >
      {state.hrRoleInputMode === "roleDescription" ? (
        <Field label={`${ui.hrRoleDescriptionLabel} (${ui.hrMarkdownSupportedSuffix})`} htmlFor="hr-role-description">
          <textarea
            id="hr-role-description"
            value={state.hrSetupForm.roleDescription}
            onChange={(event) => state.updateHrSetupField("roleDescription", event.target.value)}
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.roleDescription}
            rows={8}
            placeholder={ui.hrRoleDescriptionPlaceholder}
            className={textareaBase}
          />
        </Field>
      ) : (
        <div className="grid gap-4">
          <Field label={ui.hrRoleUrlLabel} htmlFor="hr-role-url">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <input
                id="hr-role-url"
                type="url"
                value={state.hrSetupForm.roleUrl}
                onChange={(event) => state.updateHrSetupField("roleUrl", event.target.value)}
                disabled={state.hrContextLoading || state.hrRoleFetchLoading}
                maxLength={INPUT_LIMITS.roleUrl}
                placeholder={ui.hrRoleUrlPlaceholder}
                className={inputBase}
              />
              <button
                type="button"
                onClick={state.handleFetchRoleUrl}
                disabled={state.hrContextLoading || state.hrRoleFetchLoading}
                className={secondaryButton}
              >
                {state.hrRoleFetchLoading ? ui.hrFetchingRole : ui.hrFetchRole}
              </button>
            </div>
          </Field>
          <InfoBox>{ui.hrRoleUrlHint}</InfoBox>
        </div>
      )}
      {state.hrSetupErrors.roleDescription && <InlineError message={state.hrSetupErrors.roleDescription} />}
    </DetailFrame>
  );
}

function ResumeDetail({
  state,
  ui,
  onOpenUpload,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
  onOpenUpload: () => void;
}) {
  return (
    <DetailFrame
      title={ui.hrResumeInfoTitle}
      subtitle={ui.hrResumeInfoSubtitle}
      tabs={[
        {
          id: "resumeText",
          label: ui.hrResumeTextLabel,
          active: state.hrResumeInputMode === "resumeText",
          onClick: () => state.updateHrResumeInputMode("resumeText"),
        },
        {
          id: "resumePdf",
          label: ui.hrResumePdfLabel,
          active: state.hrResumeInputMode === "resumePdf",
          onClick: () => state.updateHrResumeInputMode("resumePdf"),
        },
      ]}
    >
      {state.hrResumeInputMode === "resumeText" ? (
        <Field label={`${ui.hrResumeTextLabel} (${ui.hrMarkdownSupportedSuffix})`} htmlFor="hr-resume-text">
          <textarea
            id="hr-resume-text"
            value={state.hrSetupForm.resumeText}
            onChange={(event) => state.updateHrSetupField("resumeText", event.target.value)}
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.resumeText}
            rows={8}
            placeholder={ui.hrResumeTextPlaceholder}
            className={textareaBase}
          />
        </Field>
      ) : (
        <div className="grid gap-4">
          <button
            type="button"
            onClick={onOpenUpload}
            disabled={state.hrContextLoading || state.hrResumeExtractLoading}
            className={secondaryButton}
          >
            ⇧ {state.hrResumeExtractLoading ? ui.hrExtractingResumePdf : ui.hrExtractResumePdf}
          </button>
          <p className="text-sm text-slate-500">{ui.hrResumePdfHint}</p>
          {state.hrSetupForm.resumeText && (
            <div className="rounded-lg border border-green-100 bg-green-50 p-4 text-sm text-green-800">
              <div className="font-medium">✓ {ui.hrResumeExtractSuccessTitle}</div>
              <div>{ui.hrResumeExtractSuccessText}</div>
            </div>
          )}
          <Field label={`${ui.hrExtractedResumeTextLabel} (${ui.hrMarkdownSupportedSuffix})`} htmlFor="hr-resume-pdf-text">
            <textarea
              id="hr-resume-pdf-text"
              value={state.hrSetupForm.resumeText}
              onChange={(event) => state.updateHrSetupField("resumeText", event.target.value)}
              disabled={state.hrContextLoading}
              maxLength={INPUT_LIMITS.resumeText}
              rows={7}
              placeholder={ui.hrResumeTextPlaceholder}
              className={textareaBase}
            />
          </Field>
        </div>
      )}
      {state.hrSetupErrors.resumeText && <InlineError message={state.hrSetupErrors.resumeText} />}
    </DetailFrame>
  );
}

function ProfileDetail({
  state,
  ui,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
}) {
  return (
    <DetailFrame
      title={ui.hrProfileInfoTitle}
      subtitle={ui.hrProfileInfoSubtitle}
      tabs={[
        {
          id: "profileText",
          label: ui.hrProfileTextLabel,
          active: state.hrProfileInputMode === "profileText",
          onClick: () => state.updateHrProfileInputMode("profileText"),
        },
        {
          id: "profileUrl",
          label: ui.hrProfileUrlLabel,
          active: state.hrProfileInputMode === "profileUrl",
          onClick: () => state.updateHrProfileInputMode("profileUrl"),
        },
      ]}
    >
      {state.hrProfileInputMode === "profileText" ? (
        <Field label={`${ui.hrProfileTextLabel} (${ui.hrMarkdownSupportedSuffix})`} htmlFor="hr-profile-text">
          <textarea
            id="hr-profile-text"
            value={state.hrSetupForm.profileText}
            onChange={(event) => state.updateHrSetupField("profileText", event.target.value)}
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.profileText}
            rows={6}
            placeholder={ui.hrProfileTextPlaceholder}
            className={textareaBase}
          />
        </Field>
      ) : (
        <div className="grid gap-4">
          <Field label={ui.hrProfileUrlLabel} htmlFor="hr-profile-url">
            <div className="grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
              <input
                id="hr-profile-url"
                type="url"
                value={state.hrProfileUrl}
                onChange={(event) => state.setHrProfileUrl(event.target.value)}
                disabled={state.hrContextLoading || state.hrProfileFetchLoading}
                maxLength={INPUT_LIMITS.profileUrl}
                placeholder={ui.hrProfileUrlPlaceholder}
                className={inputBase}
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
                className={inputBase}
              />
              <button
                type="button"
                onClick={state.handleFetchSocialProfile}
                disabled={state.hrContextLoading || state.hrProfileFetchLoading}
                className={secondaryButton}
              >
                {state.hrProfileFetchLoading ? ui.hrFetchingProfile : ui.hrFetchProfile}
              </button>
            </div>
          </Field>
          <InfoBox>{ui.hrProfileFetchHint}</InfoBox>
        </div>
      )}
      {state.hrSetupErrors.profileText && <InlineError message={state.hrSetupErrors.profileText} />}
    </DetailFrame>
  );
}

function DetailFrame({
  title,
  subtitle,
  tabs,
  children,
}: {
  title: string;
  subtitle: string;
  tabs: { id: string; label: string; active: boolean; onClick: () => void }[];
  children: React.ReactNode;
}) {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      <div className="mt-6 border-b border-slate-200">
        <div className="flex w-fit rounded-lg border border-slate-200 bg-slate-50 p-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={tab.onClick}
              className={`rounded-md px-4 py-2 text-sm font-medium transition ${
                tab.active
                  ? "border border-blue-200 bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-950"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-5 grid gap-4">{children}</div>
    </div>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2">
      <label htmlFor={htmlFor} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
    </div>
  );
}

function InfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-slate-600">
      ℹ {children}
    </div>
  );
}

function InlineError({ message }: { message: string }) {
  return <p className="text-sm text-red-600">{message}</p>;
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      {message}
    </div>
  );
}

function ValidationSummary({ state }: { state: HrWorkflowState }) {
  const errors = Object.values(state.hrSetupErrors).filter(Boolean);
  if (errors.length === 0) {
    return null;
  }
  return (
    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
      <ul className="list-inside list-disc">
        {errors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}

function ContextStatus({
  state,
  ui,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
}) {
  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold text-slate-950">{ui.hrContextSummary}</h2>
          <p className="text-sm text-slate-600">
            {ui.hrStatusLabel}: <span className="font-medium">{state.hrContextResult?.status}</span>
          </p>
        </div>
        {state.hrContextId ? (
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-600">
            {state.hrContextId}
          </span>
        ) : (
          <span className="text-sm text-amber-700">{ui.hrNoContextId}</span>
        )}
      </div>

      {state.hrContextResult?.summaries && (
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {([
            [ui.hrCompanyLabel, state.hrContextResult.summaries.company],
            [ui.hrRoleLabel, state.hrContextResult.summaries.role],
            [ui.hrCandidateLabel, state.hrContextResult.summaries.candidate],
          ] as const).map(([label, value]) =>
            value ? (
              <article key={label} className="rounded-lg border border-slate-200 bg-white p-3">
                <h3 className="font-medium text-slate-900">{label}</h3>
                <p className="mt-1 text-sm text-slate-600">{value}</p>
              </article>
            ) : null,
          )}
        </div>
      )}
    </section>
  );
}

function ResumeUploadModal({
  state,
  ui,
  onClose,
}: {
  state: HrWorkflowState;
  ui: TranslationStrings;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">{ui.hrUploadPdfTitle}</h2>
            <p className="mt-1 text-sm text-slate-500">
              {ui.hrUploadPdfSubtitle}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label={ui.closeLabel}
          >
            ×
          </button>
        </div>

        <label className="mt-6 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-600 hover:border-blue-300 hover:bg-blue-50/40">
          <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            ⇧
          </span>
          <span className="font-medium">{ui.hrDragDropPdf}</span>
          <span className="my-2">{ui.hrOrLabel}</span>
          <span className="rounded-lg border border-blue-100 px-4 py-2 text-blue-700">
            {ui.hrChooseFile}
          </span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={state.hrContextLoading || state.hrResumeExtractLoading}
            onChange={state.handleExtractResumePdf}
            className="sr-only"
          />
        </label>

        <p className="mt-4 text-sm text-slate-500">{ui.hrResumePdfHint}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {ui.cancelLabel}
          </button>
          <button
            type="button"
            onClick={onClose}
            className={primaryButton}
          >
            {state.hrResumeExtractLoading ? ui.hrExtractingResumePdf : ui.doneLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function isBusy(state: HrWorkflowState) {
  return (
    state.hrContextLoading ||
    state.hrClearLoading ||
    state.hrCompanyFetchLoading ||
    state.hrRoleFetchLoading ||
    state.hrResumeExtractLoading ||
    state.hrProfileFetchLoading ||
    state.hrInterviewLoading ||
    state.hrCandidateAnswerLoading
  );
}
