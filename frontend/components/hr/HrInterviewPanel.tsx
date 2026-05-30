import Conversation from "../Conversation";
import MessageForm from "../MessageForm";
import { INPUT_LIMITS } from "../../lib/inputLimits.mjs";
import { summarizeHrToolResult } from "../../lib/hrInterviewLogic.mjs";
import type { HrWorkflowState } from "../../hooks/useHrWorkflow";
import type { TranslationStrings } from "../../types/app";

type HrInterviewPanelProps = {
  state: HrWorkflowState;
  ui: TranslationStrings;
  presentationModeEnabled: boolean;
};

export default function HrInterviewPanel({
  state,
  ui,
  presentationModeEnabled,
}: HrInterviewPanelProps) {
  if (!state.hrContextId) {
    return null;
  }

  return (
    <section className="mt-6 flex flex-col gap-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold text-gray-900">
          {ui.hrInterviewTitle}
        </h2>
        <p className="text-sm text-gray-600">
          {ui.hrInterviewSubtitle}
        </p>
        {state.hrInterviewStatus && (
          <p className="text-sm text-gray-600">
            {ui.hrQuestionsLabel}: {state.hrInterviewStatus.counted_question_roundtrips} / {state.hrInterviewStatus.question_roundtrips_limit}
          </p>
        )}
      </div>

      {state.hrInterviewCompleted && state.hrFinalResult && (
        <section
          className={`rounded-xl p-4 flex flex-col gap-3 border ${
            state.hrResultPassed
              ? "border-green-200 bg-green-50 text-green-900"
              : "border-red-200 bg-red-50 text-red-900"
          }`}
        >
          <h3 className="text-lg font-semibold">{ui.hrFinalScoreLabel}</h3>
          <p>
            {ui.hrScoreLabel}: {typeof state.hrFinalResult.overall_score === "number"
              ? `${state.hrFinalResult.overall_score.toFixed(1)} / 10`
              : ui.notAvailable}
          </p>
          {typeof state.hrFinalResult.passed === "boolean" && (
            <p>{state.hrFinalResult.passed ? ui.hrPassedLabel : ui.hrNeedsReviewLabel}</p>
          )}

          {(state.hrFinalResult.criterion_scores?.length ?? 0) > 0 && (
            <div>
              <h4 className="font-medium">{ui.rubricLabel}</h4>
              <ul className="list-disc list-inside">
                {state.hrFinalResult.criterion_scores?.map((criterion) => (
                  <li key={criterion.criterion}>
                    {criterion.criterion}: {criterion.score.toFixed(1)} / 10
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrFinalResult.strengths?.length ?? 0) > 0 && (
            <div>
              <h4 className="font-medium">{ui.strengthsLabel}</h4>
              <ul className="list-disc list-inside">
                {state.hrFinalResult.strengths?.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrFinalResult.improvements?.length ?? 0) > 0 && (
            <div>
              <h4 className="font-medium">{ui.improvementsLabel}</h4>
              <ul className="list-disc list-inside">
                {state.hrFinalResult.improvements?.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <Conversation
        conversation={state.hrConversation}
        loading={state.hrInterviewLoading}
        emptyStateText={ui.hrInterviewEmpty}
        thinkingText={ui.hrPreparingResponse}
        copyToClipboardText={ui.copyToClipboard}
        copyAllMessagesText={ui.copyAllMessages}
        copiedUserLabel={ui.copiedUserLabel}
        copiedAssistantLabel={ui.copiedAssistantLabel}
      />

      <MessageForm
        message={state.hrMessage}
        onMessageChange={state.setHrMessage}
        onSubmit={state.handleSubmitHrInterview}
        onStart={state.handleStartHrInterview}
        onClear={state.resetHrInterview}
        onEnd={state.handleEndHrInterview}
        loading={state.hrInterviewLoading}
        candidateAnswerLoading={state.hrCandidateAnswerLoading}
        canClear={state.hrConversation.length > 0}
        canEnd={state.hrHasStarted && !state.hrInterviewCompleted}
        canStart={!state.hrHasStarted}
        canGenerateCandidateAnswer={Boolean(state.latestHrInterviewerQuestion)}
        hasStarted={state.hrHasStarted}
        disableMessaging={state.hrInterviewCompleted}
        presentationModeEnabled={presentationModeEnabled}
        onGenerateCandidateAnswer={state.handleGenerateHrCandidateAnswer}
        error={state.hrInterviewError}
        placeholderStarted={
          state.hrInterviewCompleted
            ? ui.hrInterviewCompletePlaceholder
            : ui.hrAnswerPlaceholder
        }
        placeholderNotStarted={ui.hrStartFirstPlaceholder}
        startInterviewText={ui.hrStartInterview}
        startingText={ui.hrStartingInterview}
        resetConversationText={ui.hrResetInterview}
        endInterviewText={ui.endInterview}
        endingInterviewText={ui.endingInterview}
        generateCandidateAnswerText={ui.generateCandidateAnswer}
        generatingCandidateAnswerText={ui.generatingCandidateAnswer}
        sendText={ui.hrSendAnswer}
        thinkingText={ui.thinking}
        maxLength={INPUT_LIMITS.chatMessage}
      />

      {(state.hrInterviewSources.length > 0 || state.hrInterviewToolResults.length > 0 || state.hrInterviewToolCallEvents.length > 0) && (
        <div className="grid gap-4 rounded-xl border border-blue-100 bg-white p-4">
          {state.hrInterviewSources.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrRetrievedSourcesLabel}</h3>
              <ul className="mt-2 flex flex-col gap-2 text-sm text-gray-700">
                {state.hrInterviewSources.map((source, index) => (
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
                        source.title ?? source.url ?? ui.hrSourceFallback
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

          {state.hrInterviewToolResults.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrActiveToolResultsLabel}</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrInterviewToolResults.map((tool, index) => (
                  <li key={`${tool.tool_name ?? "tool"}-${index}`}>
                    {summarizeHrToolResult(tool)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {state.hrInterviewToolCallEvents.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">{ui.hrToolCallEventsLabel}</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrInterviewToolCallEvents.map((event, index) => (
                  <li key={`${event.event_id ?? "event"}-${index}`}>
                    #{event.sequence ?? index + 1} {event.tool_name ?? ui.hrToolFallback}: {event.status ?? ui.hrUnknownStatus}
                    {typeof event.duration_ms === "number" ? ` (${event.duration_ms}ms)` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
