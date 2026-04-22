import { useEffect, useRef } from "react";
import MarkdownMessage from "./MarkdownMessage";

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

type ConversationWindowProps = {
  conversation: ConversationMessage[];
  loading: boolean;
  emptyStateText: string;
  thinkingText: string;
};

export default function ConversationWindow({
  conversation,
  loading,
  emptyStateText,
  thinkingText,
}: ConversationWindowProps) {
  const conversationRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const element = conversationRef.current;
    if (!element) return;

    element.scrollTop = element.scrollHeight;
  }, [conversation, loading]);

  return (
    <section
      ref={conversationRef}
      className="w-full max-w-3xl border rounded-xl bg-white shadow-sm p-4 h-[50vh] overflow-y-auto"
    >
      {conversation.length === 0 && !loading ? (
        <p className="text-gray-500">{emptyStateText}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {conversation.map((item, index) => (
            <div
              key={`${item.role}-${index}`}
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                item.role === "user"
                  ? "self-end bg-blue-600 text-white whitespace-pre-wrap"
                  : "self-start bg-gray-100 text-gray-900"
              }`}
            >
              {item.role === "assistant" ? (
                <MarkdownMessage content={item.content} />
              ) : (
                item.content
              )}
            </div>
          ))}
          {loading && (
            <div className="self-start bg-gray-100 text-gray-900 rounded-xl px-4 py-3">
              {thinkingText}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
