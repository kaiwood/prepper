import {
  LANGUAGE_DISPLAY,
  type LanguageCode,
} from "../lib/translations";
import type { TranslationStrings } from "../types/app";

type Area = "user" | "admin" | "dashboard";

type AreaLanguageNavProps = {
  language: LanguageCode;
  selectedArea: Area;
  onAreaChange: (area: Area) => void;
  onLanguageChange: (language: LanguageCode) => void;
  ui: TranslationStrings;
};

export default function AreaLanguageNav({
  language,
  selectedArea,
  onAreaChange,
  onLanguageChange,
  ui,
}: AreaLanguageNavProps) {
  return (
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto grid w-full max-w-[1480px] grid-cols-1 items-center gap-4 px-4 py-5 sm:px-8 lg:grid-cols-[1fr_auto_1fr]">
        <nav aria-label="Area navigation" className="flex gap-3">
          {([
            ["user", ui.navUser],
            ["admin", ui.navAdmin],
            ["dashboard", ui.navDashboard],
          ] as const).map(([area, label]) => {
            const isActive = selectedArea === area;

            return (
              <button
                key={area}
                type="button"
                onClick={() => onAreaChange(area)}
                className={`rounded-lg border px-5 py-3 text-sm font-medium shadow-sm transition-colors ${
                  isActive
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {label}
              </button>
            );
          })}
        </nav>

        <div className="text-center lg:col-start-2">
          <div className="text-2xl font-bold tracking-tight text-slate-950">
            {ui.appTitle}
          </div>
          <div className="mt-1 text-sm text-slate-500">{ui.appSubtitle}</div>
        </div>

        <div className="flex gap-3 lg:justify-end">
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
                className={`rounded-lg border px-3 py-3 text-lg shadow-sm transition-colors ${
                  isActive
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {item.flag}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
