"use client";

import { useEffect, useRef } from "react";

type MessageFormProps = {
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  onStart: () => void;
  onClear: () => void;
  onEnd?: () => void;
  onGenerateCandidateAnswer?: () => void;
  loading: boolean;
  candidateAnswerLoading?: boolean;
  canClear: boolean;
  canEnd?: boolean;
  canStart: boolean;
  canGenerateCandidateAnswer?: boolean;
  hasStarted: boolean;
  disableMessaging?: boolean;
  presentationModeEnabled?: boolean;
  error: string | null;
  placeholderStarted: string;
  placeholderNotStarted: string;
  startInterviewText: string;
  startingText: string;
  resetConversationText: string;
  endInterviewText?: string;
  endingInterviewText?: string;
  generateCandidateAnswerText?: string;
  generatingCandidateAnswerText?: string;
  sendText: string;
  thinkingText: string;
  injectionWarningText?: string | null;
  maxLength?: number;
};

export default function MessageForm({
  message,
  onMessageChange,
  onSubmit,
  onStart,
  onClear,
  onEnd,
  onGenerateCandidateAnswer,
  loading,
  candidateAnswerLoading = false,
  canClear,
  canEnd = false,
  canStart,
  canGenerateCandidateAnswer = false,
  hasStarted,
  disableMessaging = false,
  presentationModeEnabled = false,
  error,
  placeholderStarted,
  placeholderNotStarted,
  startInterviewText,
  startingText,
  resetConversationText,
  endInterviewText = "End interview",
  endingInterviewText = "Ending...",
  generateCandidateAnswerText = "Draft",
  generatingCandidateAnswerText = "Drafting...",
  sendText,
  thinkingText,
  injectionWarningText = null,
  maxLength,
}: MessageFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const computed = window.getComputedStyle(textarea);
    const lineHeight = Number.parseFloat(computed.lineHeight) || 24;
    const paddingTop = Number.parseFloat(computed.paddingTop) || 0;
    const paddingBottom = Number.parseFloat(computed.paddingBottom) || 0;
    const maxHeight = lineHeight * 3 + paddingTop + paddingBottom;

    textarea.style.height = "auto";
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY =
      textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [message]);

  useEffect(() => {
    if (!loading && hasStarted) {
      textareaRef.current?.focus();
    }
  }, [hasStarted, loading]);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    onSubmit(event);
    textareaRef.current?.focus();
  };

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-4 rounded-b-xl border border-t-0 border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex items-center gap-3">
        <textarea
          ref={textareaRef}
          rows={1}
          className="min-h-14 flex-1 resize-none rounded-lg border border-slate-200 bg-white px-4 py-4 text-slate-900 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
          placeholder={hasStarted ? placeholderStarted : placeholderNotStarted}
          value={message}
          disabled={!hasStarted || loading || disableMessaging}
          maxLength={maxLength}
          onChange={(e) => onMessageChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (hasStarted && !loading && !disableMessaging && message.trim()) {
                formRef.current?.requestSubmit();
              }
            }
          }}
        />

      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {!hasStarted ? (
            <button
              type="button"
              onClick={onStart}
              disabled={loading || !canStart}
              className="rounded-lg bg-slate-950 px-4 py-3 font-medium text-white shadow-md transition-colors hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? startingText : startInterviewText}
            </button>
          ) : onEnd && !disableMessaging ? (
            <button
              type="button"
              onClick={onEnd}
              disabled={loading || !canEnd}
              className="rounded-lg bg-slate-950 px-4 py-3 font-medium text-white shadow-md transition-colors hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              □ {loading ? endingInterviewText : endInterviewText}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClear}
            disabled={loading || !canClear}
            className="rounded-lg border border-slate-200 bg-white px-4 py-3 font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ↻ {resetConversationText}
          </button>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {presentationModeEnabled && (
            <button
              type="button"
              onClick={onGenerateCandidateAnswer}
              disabled={
                !hasStarted ||
                loading ||
                candidateAnswerLoading ||
                disableMessaging ||
                !canGenerateCandidateAnswer
              }
              className="rounded-lg border border-blue-200 bg-white px-4 py-3 font-medium text-blue-700 shadow-sm transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {candidateAnswerLoading
                ? generatingCandidateAnswerText
                : generateCandidateAnswerText}
            </button>
          )}

          <button
            type="submit"
            disabled={
              !hasStarted || loading || disableMessaging || !message.trim()
            }
            className="rounded-lg bg-blue-600 px-5 py-3 font-medium text-white shadow-md transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ↗ {loading && hasStarted ? thinkingText : sendText}
          </button>
        </div>
      </div>

      {error && <p className="text-red-600 max-w-lg">{error}</p>}
      {injectionWarningText && (
        <p className="text-amber-700 max-w-lg">{injectionWarningText}</p>
      )}
    </form>
  );
}
