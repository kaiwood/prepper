import {
  LANGUAGE_DISPLAY,
  type LanguageCode,
} from "../lib/translations";

type Area = "user" | "admin";

type AreaLanguageNavProps = {
  language: LanguageCode;
  selectedArea: Area;
  onAreaChange: (area: Area) => void;
  onLanguageChange: (language: LanguageCode) => void;
};

export default function AreaLanguageNav({
  language,
  selectedArea,
  onAreaChange,
  onLanguageChange,
}: AreaLanguageNavProps) {
  return (
    <div className="w-full max-w-3xl flex items-center justify-between gap-4">
      <nav aria-label="Area navigation" className="flex gap-2">
        {([
          ["user", "User"],
          ["admin", "Admin"],
        ] as const).map(([area, label]) => {
          const isActive = selectedArea === area;

          return (
            <button
              key={area}
              type="button"
              onClick={() => onAreaChange(area)}
              className={`rounded-md border px-3 py-1 text-sm font-medium transition-colors ${
                isActive
                  ? "border-blue-600 bg-blue-50 text-blue-700"
                  : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              {label}
            </button>
          );
        })}
      </nav>

      <div className="flex gap-2">
        {(Object.keys(LANGUAGE_DISPLAY) as LanguageCode[]).map((code) => {
          const isActive = code === language;
          const item = LANGUAGE_DISPLAY[code];

          return (
            <button
              key={code}
              type="button"
              onClick={() => onLanguageChange(code)}
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
    </div>
  );
}
