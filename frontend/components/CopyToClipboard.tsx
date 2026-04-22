type CopyToClipboardProps = {
  onClick: () => void;
  label: string;
  title: string;
  pressed: boolean;
  buttonClassName: string;
};

export default function CopyToClipboard({
  onClick,
  label,
  title,
  pressed,
  buttonClassName,
}: CopyToClipboardProps) {
  return (
    <>
      <button
        type="button"
        onClick={onClick}
        aria-label={label}
        title={title}
        className={`peer ${buttonClassName}`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="relative top-[1px] left-[1px] h-4 w-4"
        >
          <path d="M16 1H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h2v2H4a4 4 0 0 1-4-4V3a4 4 0 0 1 4-4h12a4 4 0 0 1 4 4v4h-2V5a2 2 0 0 0-2-2Z" />
          <path d="M8 5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H8Zm0 2h12v12H8V7Z" />
        </svg>
      </button>
      <span
        className={`pointer-events-none absolute -top-8 right-0 hidden rounded bg-gray-900 px-2 py-1 text-[11px] text-white shadow-sm transition-all duration-200 ${
          pressed ? "" : "peer-hover:inline-flex"
        }`}
      >
        {label}
      </span>
    </>
  );
}
