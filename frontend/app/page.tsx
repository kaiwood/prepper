"use client";

import { useEffect, useSyncExternalStore, useState } from "react";
import Conversation, {
  type ConversationMessage,
} from "../components/Conversation";
import MessageForm from "../components/MessageForm";
import PromptSelector from "../components/PromptSelector";
import {
  LANGUAGE_DISPLAY,
  LANGUAGE_STORAGE_KEY,
  TRANSLATIONS,
  type LanguageCode,
} from "../lib/translations";

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

const DEFAULT_LANGUAGE: LanguageCode = "en";
const LANGUAGE_CHANGE_EVENT = "prepper-language-change";

function readStoredLanguage(): LanguageCode {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return storedLanguage === "en" || storedLanguage === "de"
    ? storedLanguage
    : DEFAULT_LANGUAGE;
}

function subscribeLanguageChange(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleChange = () => onStoreChange();
  window.addEventListener("storage", handleChange);
  window.addEventListener(LANGUAGE_CHANGE_EVENT, handleChange);

  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(LANGUAGE_CHANGE_EVENT, handleChange);
  };
}

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
  const language = useSyncExternalStore(
    subscribeLanguageChange,
    readStoredLanguage,
    () => DEFAULT_LANGUAGE,
  );
  const hasStarted = conversation.length > 0;
  const ui = TRANSLATIONS[language];

  const updateLanguage = (nextLanguage: LanguageCode) => {
    if (typeof window === "undefined") {
      return;
    }

    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    window.dispatchEvent(new Event(LANGUAGE_CHANGE_EVENT));
  };

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
            setPromptsError(data.error ?? ui.errorLoadPrompts);
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
          setPromptsError(ui.errorLoadPrompts);
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
  }, [ui.errorLoadPrompts]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!hasStarted || !message.trim() || loading) return;

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
        language: LanguageCode;
      } = {
        message: prompt,
        conversation_history: history,
        language,
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
        setError(data.error ?? ui.errorFallback);
      } else {
        setConversation((prev) => [
          ...prev,
          { role: "assistant", content: data.reply ?? "" },
        ]);
      }
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }

  async function handleStart() {
    if (loading || promptsLoading || hasStarted || !selectedPrompt) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: { system_prompt_name?: string; language: LanguageCode } = {
        language,
      };

      if (selectedPrompt) {
        payload.system_prompt_name = selectedPrompt;
      }

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/chat/start`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? ui.errorFallback);
      } else {
        setConversation([{ role: "assistant", content: data.reply ?? "" }]);
      }
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center p-8 gap-6">
      <div className="w-full max-w-3xl flex justify-end gap-2">
        {(Object.keys(LANGUAGE_DISPLAY) as LanguageCode[]).map((code) => {
          const isActive = code === language;
          const item = LANGUAGE_DISPLAY[code];

          return (
            <button
              key={code}
              type="button"
              onClick={() => updateLanguage(code)}
              aria-label={item.label}
              title={item.label}
              className={`rounded-md border px-2 py-1 text-sm transition-colors ${
                isActive
                  ? "border-blue-600 bg-blue-50"
                  : "border-gray-300 bg-white hover:bg-gray-50"
              }`}
            >
              {item.flag}
            </button>
          );
        })}
      </div>

      <h1 className="text-3xl font-bold mt-2">{ui.appTitle}</h1>
      <p className="text-gray-500">{ui.appSubtitle}</p>

      <PromptSelector
        prompts={availablePrompts}
        selectedPrompt={selectedPrompt}
        onPromptChange={setSelectedPrompt}
        loading={promptsLoading || loading}
        locked={hasStarted}
        error={promptsError}
        label={ui.promptLabel}
        loadingText={ui.promptLoading}
        unavailableText={ui.promptUnavailable}
        lockedHint={ui.promptLockedHint}
      />

      <Conversation
        conversation={conversation}
        loading={loading}
        emptyStateText={ui.conversationEmpty}
        thinkingText={ui.thinking}
      />

      <MessageForm
        message={message}
        onMessageChange={setMessage}
        onSubmit={handleSubmit}
        onStart={handleStart}
        onClear={() => {
          setConversation([]);
          setMessage("");
          setError(null);
        }}
        loading={loading}
        canClear={conversation.length > 0}
        canStart={Boolean(selectedPrompt) && availablePrompts.length > 0}
        hasStarted={hasStarted}
        error={error}
        placeholderStarted={ui.inputPlaceholderStarted}
        placeholderNotStarted={ui.inputPlaceholderNotStarted}
        startInterviewText={ui.startInterview}
        startingText={ui.starting}
        resetConversationText={ui.resetConversation}
        sendText={ui.send}
        thinkingText={ui.thinking}
      />
    </main>
  );
}
