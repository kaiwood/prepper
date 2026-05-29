import Conversation from "./Conversation";
import MessageForm from "./MessageForm";
import PromptSelector from "./PromptSelector";
import { INPUT_LIMITS } from "../lib/inputLimits.mjs";
import {
  ADVANCED_SETTING_CONFIG,
  formatAdvancedSettingValue,
} from "../lib/appLogic.mjs";
import type { UserInterviewState } from "../hooks/useUserInterview";
import type {
  AdvancedSettingConfig,
  AdvancedSettingField,
  DifficultyValue,
  TranslationStrings,
} from "../types/app";

const TYPED_ADVANCED_SETTING_CONFIG =
  ADVANCED_SETTING_CONFIG as AdvancedSettingConfig[];

type UserInterviewPanelProps = {
  state: UserInterviewState;
  ui: TranslationStrings;
  presentationModeEnabled: boolean;
};

export default function UserInterviewPanel({
  state,
  ui,
  presentationModeEnabled,
}: UserInterviewPanelProps) {
  return (
    <>
      <h1 className="text-3xl font-bold mt-2">{ui.appTitle}</h1>
      <p className="text-gray-500">{ui.appSubtitle}</p>

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
        <div className="w-full max-w-3xl flex flex-col">
          <div className="flex items-center justify-between gap-3">
            {state.interviewRatingEnabled || state.difficultyEnabled ? (
              <button
                type="button"
                onClick={() => state.setSettingsOpen((prev) => !prev)}
                className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                <span
                  className={`inline-block transition-transform duration-300 text-xs ${
                    state.settingsOpen ? "rotate-90" : "rotate-0"
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
              onClick={() => state.setAdvancedSettingsOpen((prev) => !prev)}
              className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              <span
                className={`inline-block transition-transform duration-300 text-xs ${
                  state.advancedSettingsOpen ? "rotate-90" : "rotate-0"
                }`}
              >
                ▶
              </span>
              {ui.advancedSettingsLabel}
            </button>
          </div>

          {(state.interviewRatingEnabled || state.difficultyEnabled) && (
            <div
              className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
                state.settingsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <div className="flex flex-col gap-6 pt-4">
                  {state.interviewRatingEnabled && (
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
                          state.selectedPromptMetadata
                            .min_question_roundtrips ?? 1
                        }
                        max={
                          state.selectedPromptMetadata
                            .max_question_roundtrips ?? 10
                        }
                        value={state.questionRoundtripLimit}
                        disabled={state.hasStarted || state.loading}
                        onChange={(event) => {
                          const raw = Number.parseInt(event.target.value, 10);
                          const min =
                            state.selectedPromptMetadata
                              ?.min_question_roundtrips ?? 1;
                          const max =
                            state.selectedPromptMetadata
                              ?.max_question_roundtrips ?? 10;
                          if (Number.isNaN(raw)) {
                            state.setQuestionRoundtripLimit(min);
                            return;
                          }
                          state.setQuestionRoundtripLimit(
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

                  {state.difficultyEnabled && (
                    <section className="flex flex-col gap-2">
                      <label
                        htmlFor="difficulty-level"
                        className="text-sm font-medium text-gray-700"
                      >
                        {ui.difficultyLabel}
                      </label>
                      <select
                        id="difficulty-level"
                        value={state.selectedDifficulty}
                        disabled={state.hasStarted || state.loading}
                        onChange={(event) =>
                          state.setSelectedDifficulty(
                            event.target.value as DifficultyValue,
                          )
                        }
                        className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
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
              state.advancedSettingsOpen
                ? "grid-rows-[1fr]"
                : "grid-rows-[0fr]"
            }`}
          >
            <div className="overflow-hidden">
              <div className="flex flex-col gap-4 pt-4">
                <p className="text-sm text-gray-500">
                  {ui.advancedSettingsHint}
                </p>
                {TYPED_ADVANCED_SETTING_CONFIG.map((config) => {
                  const value = state.advancedSettings[config.key];
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
                        disabled={state.hasStarted || state.loading}
                        onChange={(event) =>
                          state.updateAdvancedSetting(
                            config.key,
                            event.target.value,
                          )
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

      {state.interviewCompleted && state.interviewStatus?.final_result && (
        <section
          className={`w-full max-w-3xl rounded-xl p-4 flex flex-col gap-3 border ${
            state.resultPassed
              ? "border-green-200 bg-green-50 text-green-900"
              : "border-red-200 bg-red-50 text-red-900"
          }`}
        >
          <h2 className="text-xl font-semibold">{ui.interviewComplete}</h2>
          <p>
            {ui.scoreLabel}: {" "}
            {state.interviewStatus.final_result.overall_score.toFixed(1)} / 10
          </p>
          <p>
            {state.interviewStatus.final_result.passed
              ? ui.passLabel
              : ui.failLabel}
          </p>

          <div>
            <h3 className="font-medium">{ui.rubricLabel}</h3>
            <ul className="list-disc list-inside">
              {state.interviewStatus.final_result.criterion_scores.map(
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
              {state.interviewStatus.final_result.strengths.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-medium">{ui.improvementsLabel}</h3>
            <ul className="list-disc list-inside">
              {state.interviewStatus.final_result.improvements.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <Conversation
        conversation={state.conversation}
        loading={state.loading}
        emptyStateText={ui.conversationEmpty}
        thinkingText={ui.thinking}
      />

      <MessageForm
        message={state.message}
        onMessageChange={state.setMessage}
        onSubmit={state.handleSubmit}
        onStart={state.handleStart}
        onClear={state.handleClear}
        loading={state.loading}
        candidateAnswerLoading={state.candidateAnswerLoading}
        canClear={state.conversation.length > 0}
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
        generateCandidateAnswerText={ui.generateCandidateAnswer}
        generatingCandidateAnswerText={ui.generatingCandidateAnswer}
        sendText={ui.send}
        thinkingText={ui.thinking}
        injectionWarningText={
          state.showInjectionWarning ? ui.injectionWarning : null
        }
        maxLength={INPUT_LIMITS.chatMessage}
      />
    </>
  );
}
