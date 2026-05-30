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
  label: string;
  loadingText: string;
  unavailableText: string;
  lockedHint: string;
};

export default function PromptSelector({
  prompts,
  selectedPrompt,
  onPromptChange,
  loading,
  locked,
  error,
  label,
  loadingText,
  unavailableText,
  lockedHint,
}: PromptSelectorProps) {
  const hasPrompts = prompts.length > 0;

  return (
    <section className="flex w-full flex-col gap-2">
      <label
        htmlFor="system-prompt"
        className="text-sm font-medium text-slate-700"
      >
        {label}
      </label>
      <select
        id="system-prompt"
        value={selectedPrompt}
        onChange={(e) => onPromptChange(e.target.value)}
        disabled={loading || locked || !hasPrompts}
        className="h-12 rounded-lg border border-slate-200 bg-white px-5 text-base text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
      >
        {!hasPrompts ? (
          <option value="">{loading ? loadingText : unavailableText}</option>
        ) : (
          prompts.map((prompt) => (
            <option key={prompt.id} value={prompt.id}>
              {prompt.name}
            </option>
          ))
        )}
      </select>
      {locked && <p className="text-sm text-slate-500">{lockedHint}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </section>
  );
}
