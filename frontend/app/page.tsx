"use client";

import { useState } from "react";
import Conversation, {
  type ConversationMessage,
} from "../components/Conversation";
import MessageForm from "../components/MessageForm";

export default function Home() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
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

      <MessageForm
        message={message}
        onMessageChange={setMessage}
        onSubmit={handleSubmit}
        onClear={() => {
          setConversation([]);
          setError(null);
        }}
        loading={loading}
        canClear={conversation.length > 0}
        error={error}
      />
    </main>
  );
}
