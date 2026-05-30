import Conversation from "./Conversation";
import MessageForm from "./MessageForm";
import PromptSelector from "./PromptSelector";
import { INPUT_LIMITS } from "../lib/inputLimits.mjs";
import type { UserInterviewState } from "../hooks/useUserInterview";
import type {
  DifficultyValue,
  TranslationStrings,
} from "../types/app";
const HR_CANDIDATE_FIT_PROMPT = "hr_candidate_fit";

type UserInterviewPanelProps = {
  state: UserInterviewState;
  ui: TranslationStrings;
  presentationModeEnabled: boolean;
  onEditContext: () => void;
};

export default function UserInterviewPanel({
  state,
  ui,
  presentationModeEnabled,
  onEditContext,
}: UserInterviewPanelProps) {
  const showHrEnd = state.selectedPrompt === HR_CANDIDATE_FIT_PROMPT;
  const canEnd = Boolean(
    showHrEnd && state.hasStarted && !state.interviewCompleted,
  );

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_400px]">
      <section className="min-w-0">
        <div className="mb-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
          <PromptSelector
            prompts={state.availablePrompts}
            selectedPrompt={state.selectedPrompt}
            onPromptChange={state.handlePromptChange}
            loading={state.promptsLoading || state.loading}
            locked={state.hasStarted}
            error={state.promptsError}
            label={ui.promptLabel}
            loadingText={ui.promptLoading}
            unavailableText={ui.promptUnavailable}
            lockedHint={ui.promptLockedHint}
          />

          {state.selectedPromptMetadata && (
            <div className="flex items-start px-1 text-slate-600 lg:pt-7">
              {(state.interviewRatingEnabled || state.difficultyEnabled) && (
                <button
                  type="button"
                  onClick={() => state.setSettingsOpen((prev) => !prev)}
                  className="inline-flex min-h-12 items-center gap-2 rounded-lg border border-slate-200 bg-white px-5 text-base font-medium shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950"
                >
                  <span className="text-3xl leading-none">⚙</span>
                  {ui.settingsLabel}
                </button>
              )}
            </div>
          )}
        </div>

        {state.selectedPromptMetadata && (
          <InterviewSettings state={state} ui={ui} />
        )}

        {state.interviewCompleted && state.interviewStatus?.final_result && (
          <section
            className={`mb-5 rounded-xl border p-4 shadow-sm ${
              state.resultPassed
                ? "border-green-200 bg-green-50 text-green-900"
                : "border-red-200 bg-red-50 text-red-900"
            }`}
          >
            <h2 className="text-xl font-semibold">{ui.interviewComplete}</h2>
            <p className="mt-2">
              {ui.scoreLabel}: {" "}
              {state.interviewStatus.final_result.overall_score.toFixed(1)} / 10
            </p>
            <p>
              {state.interviewStatus.final_result.passed
                ? ui.passLabel
                : ui.failLabel}
            </p>
          </section>
        )}

        <div className="rounded-xl border border-slate-200 bg-white p-0 shadow-sm">
          <Conversation
            conversation={state.conversation}
            loading={state.loading}
            emptyStateText={ui.conversationEmpty}
            thinkingText={ui.thinking}
            copyToClipboardText={ui.copyToClipboard}
            copyAllMessagesText={ui.copyAllMessages}
            copiedUserLabel={ui.copiedUserLabel}
            copiedAssistantLabel={ui.copiedAssistantLabel}
          />

          <MessageForm
            message={state.message}
            onMessageChange={state.setMessage}
            onSubmit={state.handleSubmit}
            onStart={state.handleStart}
            onEnd={showHrEnd ? state.handleEndInterview : undefined}
            onClear={state.handleClear}
            loading={state.loading}
            candidateAnswerLoading={state.candidateAnswerLoading}
            canClear={state.conversation.length > 0}
            canEnd={canEnd}
            canStart={Boolean(state.selectedPrompt) && state.availablePrompts.length > 0}
            hasStarted={state.hasStarted}
            disableMessaging={state.interviewCompleted}
            presentationModeEnabled={presentationModeEnabled}
            canGenerateCandidateAnswer={Boolean(state.latestInterviewerQuestion)}
            onGenerateCandidateAnswer={state.handleGenerateCandidateAnswer}
            error={state.error}
            placeholderStarted={
              state.interviewCompleted
                ? ui.interviewLockedPlaceholder
                : ui.inputPlaceholderStarted
            }
            placeholderNotStarted={ui.inputPlaceholderNotStarted}
            startInterviewText={ui.startInterview}
            startingText={ui.starting}
            resetConversationText={ui.resetConversation}
            endInterviewText={ui.endInterview}
            endingInterviewText={ui.endingInterview}
            generateCandidateAnswerText={ui.generateCandidateAnswer}
            generatingCandidateAnswerText={ui.generatingCandidateAnswer}
            sendText={ui.send}
            thinkingText={ui.thinking}
            injectionWarningText={
              state.showInjectionWarning ? ui.injectionWarning : null
            }
            maxLength={INPUT_LIMITS.chatMessage}
          />
        </div>
      </section>

      <InterviewSidebar state={state} ui={ui} onEditContext={onEditContext} />
    </div>
  );
}

function InterviewSettings({
  state,
  ui,
}: {
  state: UserInterviewState;
  ui: TranslationStrings;
}) {
  return (
    <div className="mb-5 grid gap-4">
      {(state.interviewRatingEnabled || state.difficultyEnabled) && state.settingsOpen && (
        <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2">
          {state.interviewRatingEnabled && (
            <div className="flex flex-col gap-2">
              <label
                htmlFor="roundtrip-limit"
                className="text-sm font-medium text-slate-700"
              >
                {ui.questionLimitLabel}
              </label>
              <input
                id="roundtrip-limit"
                type="number"
                min={state.selectedPromptMetadata?.min_question_roundtrips ?? 1}
                max={state.selectedPromptMetadata?.max_question_roundtrips ?? 10}
                value={state.questionRoundtripLimit}
                disabled={state.hasStarted || state.loading}
                onChange={(event) => {
                  const raw = Number.parseInt(event.target.value, 10);
                  const min = state.selectedPromptMetadata?.min_question_roundtrips ?? 1;
                  const max = state.selectedPromptMetadata?.max_question_roundtrips ?? 10;
                  state.setQuestionRoundtripLimit(
                    Number.isNaN(raw) ? min : Math.max(min, Math.min(max, raw)),
                  );
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
              />
              <p className="text-sm text-slate-500">{ui.questionLimitHint}</p>
            </div>
          )}

          {state.difficultyEnabled && (
            <div className="flex flex-col gap-2">
              <label
                htmlFor="difficulty-level"
                className="text-sm font-medium text-slate-700"
              >
                {ui.difficultyLabel}
              </label>
              <select
                id="difficulty-level"
                value={state.selectedDifficulty}
                disabled={state.hasStarted || state.loading}
                onChange={(event) =>
                  state.setSelectedDifficulty(event.target.value as DifficultyValue)
                }
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
              >
                {state.difficultyLevels
                  .filter((level): level is DifficultyValue =>
                    ["easy", "medium", "hard"].includes(level),
                  )
                  .map((level) => (
                    <option key={level} value={level}>
                      {state.difficultyLabelByValue[level]}
                    </option>
                  ))}
              </select>
              <p className="text-sm text-slate-500">{ui.difficultyHint}</p>
            </div>
          )}
        </section>
      )}

    </div>
  );
}

function InterviewSidebar({
  state,
  ui,
  onEditContext,
}: {
  state: UserInterviewState;
  ui: TranslationStrings;
  onEditContext: () => void;
}) {
  const summaries = state.hrContextResult?.summaries;
  const contextRows = [
    {
      icon: "⌘",
      label: ui.hrCompanyLabel,
      value: summaries?.company ?? ui.notConfiguredLabel,
    },
    {
      icon: "♙",
      label: ui.hrRoleLabel,
      value: summaries?.role ?? ui.notConfiguredLabel,
    },
    {
      icon: "▤",
      label: ui.hrResumeLabel,
      value: summaries?.candidate ?? ui.notConfiguredLabel,
    },
    {
      icon: "✎",
      label: ui.hrProfileLabel,
      value: state.hrContextResult?.context_id
        ? ui.profileOptionalContextIncluded
        : ui.hrOptionalLabel,
    },
  ];

  return (
    <aside className="grid h-fit gap-6">
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="font-semibold text-slate-950">{ui.interviewContextTitle}</h2>
          <button
            type="button"
            onClick={onEditContext}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:bg-slate-50"
          >
            ✎ {ui.editLabel}
          </button>
        </div>
        <div className="divide-y divide-slate-100 px-5">
          {contextRows.map((item) => (
            <article key={item.label} className="flex items-center gap-4 py-5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                {item.icon}
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-slate-900">{item.label}</h3>
                <p className="line-clamp-2 text-sm text-slate-500">{item.value}</p>
              </div>
              <span className="text-xl text-slate-400">›</span>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            ♢
          </div>
          <h2 className="font-semibold text-slate-950">{ui.aiAssistantTitle}</h2>
        </div>
        <div className="space-y-5 px-6 py-5 text-sm text-slate-600">
          <p>{ui.aiAssistantIntro}</p>
          <ul className="space-y-3">
            {[
              ui.aiAssistantFollowUpQuestions,
              ui.aiAssistantFeedback,
              ui.aiAssistantTips,
              ui.aiAssistantInsights,
            ].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="text-green-600">✓</span>
                {item}
              </li>
            ))}
          </ul>
          <div className="rounded-lg border border-blue-100 bg-blue-50/70 p-4 text-slate-700">
            <div className="font-semibold text-slate-900">🔒 {ui.secureDataTitle}</div>
            <div className="mt-1">{ui.secureDataSubtitle}</div>
          </div>
        </div>
      </section>
    </aside>
  );
}
