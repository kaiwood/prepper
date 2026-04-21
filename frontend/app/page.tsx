"use client";

import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setReply(null);
    setError(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? "Something went wrong.");
      } else {
        setReply(data.reply);
      }
    } catch {
      setError("Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 gap-6">
      <h1 className="text-3xl font-bold">Prepper</h1>
      <p className="text-gray-500">Interview preparation, powered by AI.</p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full max-w-lg">
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
      </form>

      {error && (
        <p className="text-red-600 max-w-lg">{error}</p>
      )}

      {reply && (
        <div className="border rounded-lg p-4 max-w-lg w-full bg-gray-50 whitespace-pre-wrap">
          {reply}
        </div>
      )}
    </main>
  );
}
