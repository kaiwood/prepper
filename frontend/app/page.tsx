"use client";

import { useState } from "react";

type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

      <section className="w-full max-w-3xl border rounded-xl bg-white shadow-sm p-4 h-[50vh] overflow-y-auto">
        {conversation.length === 0 ? (
          <p className="text-gray-500">
            Start a conversation. Your recent context will be used in follow-up
            replies.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {conversation.map((item, index) => (
              <div
                key={`${item.role}-${index}`}
                className={`max-w-[80%] rounded-xl px-4 py-3 whitespace-pre-wrap ${
                  item.role === "user"
                    ? "self-end bg-blue-600 text-white"
                    : "self-start bg-gray-100 text-gray-900"
                }`}
              >
                {item.content}
              </div>
            ))}
            {loading && (
              <div className="self-start bg-gray-100 text-gray-900 rounded-xl px-4 py-3">
                Thinking...
              </div>
            )}
          </div>
        )}
      </section>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 w-full max-w-3xl"
      >
        <textarea
          className="border rounded-lg p-3 resize-none h-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Ask a question or describe the role you're preparing for…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
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
