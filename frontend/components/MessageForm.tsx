"use client";

import { useEffect, useRef } from "react";

type MessageFormProps = {
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  onStart: () => void;
  onClear: () => void;
  loading: boolean;
  canClear: boolean;
  canStart: boolean;
  hasStarted: boolean;
  disableMessaging?: boolean;
  error: string | null;
  placeholderStarted: string;
  placeholderNotStarted: string;
  startInterviewText: string;
  startingText: string;
  resetConversationText: string;
  sendText: string;
  thinkingText: string;
  injectionWarningText?: string | null;
};

export default function MessageForm({
  message,
  onMessageChange,
  onSubmit,
  onStart,
  onClear,
  loading,
  canClear,
  canStart,
  hasStarted,
  disableMessaging = false,
  error,
  placeholderStarted,
  placeholderNotStarted,
  startInterviewText,
  startingText,
  resetConversationText,
  sendText,
  thinkingText,
  injectionWarningText = null,
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
      className="flex flex-col gap-3 w-full max-w-3xl"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        className="border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder={hasStarted ? placeholderStarted : placeholderNotStarted}
        value={message}
        disabled={!hasStarted || loading || disableMessaging}
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

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={onStart}
            disabled={loading || hasStarted || !canStart}
            className="bg-gray-900 text-white rounded-lg py-2 px-4 hover:bg-black disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading && !hasStarted ? startingText : startInterviewText}
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={loading || !canClear}
            className="border border-gray-300 text-gray-700 rounded-lg py-2 px-4 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {resetConversationText}
          </button>
        </div>

        <button
          type="submit"
          disabled={
            !hasStarted || loading || disableMessaging || !message.trim()
          }
          className="bg-blue-600 text-white rounded-lg py-2 px-4 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading && hasStarted ? thinkingText : sendText}
        </button>
      </div>

      {error && <p className="text-red-600 max-w-lg">{error}</p>}
      {injectionWarningText && (
        <p className="text-amber-700 max-w-lg">{injectionWarningText}</p>
      )}
    </form>
  );
}
