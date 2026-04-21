"use client";

import { useEffect, useRef, useState } from "react";
import Conversation, {
  type ConversationMessage,
} from "../components/Conversation";

export default function Home() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || loading) return;

    const prompt = message.trim();
    const history = [...conversation];
    setConversation((prev) => [...prev, { role: "user", content: prompt }]);
    setMessage("");

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: prompt,
          conversation_history: history,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? "Something went wrong.");
      } else {
        setConversation((prev) => [
          ...prev,
          { role: "assistant", content: data.reply ?? "" },
        ]);
      }
    } catch {
      setError("Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 gap-6">
      <h1 className="text-3xl font-bold mt-6">Prepper</h1>
      <p className="text-gray-500">Interview preparation, powered by AI.</p>

      <Conversation conversation={conversation} loading={loading} />

      <form
        ref={formRef}
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 w-full max-w-3xl"
      >
        <textarea
          ref={textareaRef}
          rows={1}
          className="border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Ask a question or describe the role you're preparing for…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!loading && message.trim()) {
                formRef.current?.requestSubmit();
              }
            }
          }}
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          className="bg-blue-600 text-white rounded-lg py-2 px-4 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Thinking…" : "Send"}
        </button>
        <button
          type="button"
          onClick={() => {
            setConversation([]);
            setError(null);
          }}
          disabled={loading || conversation.length === 0}
          className="border border-gray-300 text-gray-700 rounded-lg py-2 px-4 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Clear conversation
        </button>
      </form>

      {error && <p className="text-red-600 max-w-lg">{error}</p>}
    </main>
  );
}
