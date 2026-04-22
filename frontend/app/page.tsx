"use client";

import { useEffect, useState } from "react";
import Conversation, {
  type ConversationMessage,
} from "../components/Conversation";
import MessageForm from "../components/MessageForm";
import PromptSelector from "../components/PromptSelector";

type PromptMetadata = {
  id: string;
  name: string;
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  max_tokens: number;
};

type PromptsResponse = {
  prompts?: PromptMetadata[];
  default?: string;
  error?: string;
};

export default function Home() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [availablePrompts, setAvailablePrompts] = useState<PromptMetadata[]>(
    [],
  );
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [promptsLoading, setPromptsLoading] = useState(true);
  const [promptsError, setPromptsError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadPrompts() {
      setPromptsLoading(true);
      setPromptsError(null);

      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/prompts`,
        );
        const data: PromptsResponse = await res.json();

        if (!res.ok) {
          if (!isCancelled) {
            setPromptsError(data.error ?? "Could not load system prompts.");
          }
          return;
        }

        const prompts = Array.isArray(data.prompts)
          ? data.prompts.filter(
              (p): p is PromptMetadata =>
                typeof p === "object" &&
                p !== null &&
                typeof p.id === "string" &&
                typeof p.name === "string",
            )
          : [];
        const defaultPrompt =
          typeof data.default === "string" ? data.default : "";

        if (!isCancelled) {
          setAvailablePrompts(prompts);

          if (prompts.length > 0) {
            const ids = prompts.map((p) => p.id);
            setSelectedPrompt(
              ids.includes(defaultPrompt) ? defaultPrompt : ids[0],
            );
          }
        }
      } catch {
        if (!isCancelled) {
          setPromptsError("Could not load system prompts.");
        }
      } finally {
        if (!isCancelled) {
          setPromptsLoading(false);
        }
      }
    }

    void loadPrompts();

    return () => {
      isCancelled = true;
    };
  }, []);

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
      const payload: {
        message: string;
        conversation_history: ConversationMessage[];
        system_prompt_name?: string;
      } = {
        message: prompt,
        conversation_history: history,
      };

      if (selectedPrompt) {
        payload.system_prompt_name = selectedPrompt;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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

      <PromptSelector
        prompts={availablePrompts}
        selectedPrompt={selectedPrompt}
        onPromptChange={setSelectedPrompt}
        loading={promptsLoading || loading}
        error={promptsError}
      />

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
