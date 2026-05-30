import { useEffect, useRef, useState } from "react";
import CopyToClipboard from "./CopyToClipboard";
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
  copyToClipboardText: string;
  copyAllMessagesText: string;
  copiedUserLabel: string;
  copiedAssistantLabel: string;
};

export default function ConversationWindow({
  conversation,
  loading,
  emptyStateText,
  thinkingText,
  copyToClipboardText,
  copyAllMessagesText,
  copiedUserLabel,
  copiedAssistantLabel,
}: ConversationWindowProps) {
  const conversationRef = useRef<HTMLElement>(null);
  const [pressedCopyButton, setPressedCopyButton] = useState<string | null>(
    null,
  );
  const [showCopyAllButton, setShowCopyAllButton] = useState(false);

  useEffect(() => {
    const element = conversationRef.current;
    if (!element) return;

    element.scrollTop = element.scrollHeight;
  }, [conversation, loading]);

  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch (error) {
      console.error("Failed to copy message", error);
    }
  };

  const getConversationMarkdown = () => {
    return conversation
      .map((item) => {
        const roleLabel = item.role === "user" ? copiedUserLabel : copiedAssistantLabel;
        return `**${roleLabel}:**\n${item.content}`;
      })
      .join("\n\n");
  };

  const handleCopyAllMessages = async () => {
    await handleCopyMessage(getConversationMarkdown());
  };

  const handleConversationMouseMove = (
    event: React.MouseEvent<HTMLElement>,
  ) => {
    const target = event.target as HTMLElement;
    const overMessage = Boolean(target.closest("[data-message]"));
    setShowCopyAllButton(!overMessage);
  };

  const handleConversationMouseLeave = () => {
    setShowCopyAllButton(false);
  };

  return (
    <section
      ref={conversationRef}
      onMouseMove={handleConversationMouseMove}
      onMouseLeave={handleConversationMouseLeave}
      className="relative h-[55vh] w-full overflow-y-auto rounded-t-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {conversation.length === 0 && !loading ? (
        <p className="text-slate-500">{emptyStateText}</p>
      ) : (
        <>
          <div className="flex flex-col gap-5">
            {conversation.map((item, index) => (
              <div
                key={`${item.role}-${index}`}
                data-message="true"
                className={`group relative max-w-[82%] rounded-xl border px-5 pb-4 pt-4 shadow-sm ${
                  item.role === "user"
                    ? "self-end border-blue-100 bg-blue-50 text-slate-950 whitespace-pre-wrap"
                    : "self-start border-slate-200 bg-white text-slate-950"
                }`}
              >
                <div className="absolute bottom-2 right-2">
                  <CopyToClipboard
                    onClick={() => {
                      setPressedCopyButton(`${item.role}-${index}`);
                      handleCopyMessage(item.content);
                    }}
                    label={copyToClipboardText}
                    title={copyToClipboardText}
                    pressed={pressedCopyButton === `${item.role}-${index}`}
                    buttonClassName="pointer-events-none opacity-0 transition-all duration-200 group-hover:opacity-100 group-hover:pointer-events-auto rounded-2xl bg-white/95 p-2 text-gray-900 shadow-sm hover:text-black active:shadow-inner active:bg-gray-200"
                  />
                </div>

                {item.role === "assistant" ? (
                  <MarkdownMessage content={item.content} />
                ) : (
                  item.content
                )}
              </div>
            ))}
            {loading && (
              <div
                data-message="true"
                className="group relative self-start rounded-xl border border-slate-200 bg-white px-5 pb-4 pt-4 text-slate-950 shadow-sm"
              >
                {thinkingText}
              </div>
            )}
          </div>
          <div className="absolute inset-x-0 bottom-2 flex justify-end pr-2 z-10">
            <CopyToClipboard
              onClick={() => {
                setPressedCopyButton("all");
                handleCopyAllMessages();
              }}
              label={copyAllMessagesText}
              title={copyAllMessagesText}
              pressed={pressedCopyButton === "all"}
              buttonClassName={`rounded-2xl bg-white/95 p-2 text-gray-900 shadow-sm hover:text-black active:shadow-inner active:bg-gray-200 transition-all duration-200 ${
                showCopyAllButton
                  ? "opacity-100 pointer-events-auto"
                  : "opacity-0 pointer-events-none"
              }`}
            />
          </div>
        </>
      )}
    </section>
  );
}
