"use client";

type PromptOption = {
  id: string;
  name: string;
};

type PromptSelectorProps = {
  prompts: PromptOption[];
  selectedPrompt: string;
  onPromptChange: (value: string) => void;
  loading: boolean;
  locked: boolean;
  error: string | null;
};

export default function PromptSelector({
  prompts,
  selectedPrompt,
  onPromptChange,
  loading,
  locked,
  error,
}: PromptSelectorProps) {
  const hasPrompts = prompts.length > 0;

  return (
    <section className="w-full max-w-3xl flex flex-col gap-2">
      <label
        htmlFor="system-prompt"
        className="text-sm font-medium text-gray-700"
      >
        Interview type
      </label>
      <select
        id="system-prompt"
        value={selectedPrompt}
        onChange={(e) => onPromptChange(e.target.value)}
        disabled={loading || locked || !hasPrompts}
        className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
      >
        {!hasPrompts ? (
          <option value="">
            {loading ? "Loading prompts..." : "Prompt list unavailable"}
          </option>
        ) : (
          prompts.map((prompt) => (
            <option key={prompt.id} value={prompt.id}>
              {prompt.name}
            </option>
          ))
        )}
      </select>
      {locked && (
        <p className="text-sm text-gray-500">
          Reset the conversation to choose a different interview.
        </p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
