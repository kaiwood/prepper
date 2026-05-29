"use client";

import { useState } from "react";
import AreaLanguageNav from "../components/AreaLanguageNav";
import UserInterviewPanel from "../components/UserInterviewPanel";
import HrSetupPanel from "../components/hr/HrSetupPanel";
import { useHrWorkflow } from "../hooks/useHrWorkflow";
import { useLanguage } from "../hooks/useLanguage";
import { useUserInterview } from "../hooks/useUserInterview";
import { TRANSLATIONS } from "../lib/translations";
import {
  resolveApiBaseUrl,
  resolvePresentationMode,
} from "../lib/appLogic.mjs";

const API_BASE_URL = resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
const PRESENTATION_MODE_ENABLED = resolvePresentationMode(
  process.env.NEXT_PUBLIC_PREPPER_PRESENTATION_MODE,
);

type Area = "user" | "admin";

export default function Home() {
  const [selectedArea, setSelectedArea] = useState<Area>("user");
  const { language, updateLanguage } = useLanguage();
  const ui = TRANSLATIONS[language];
  const userInterview = useUserInterview({
    apiBaseUrl: API_BASE_URL,
    presentationModeEnabled: PRESENTATION_MODE_ENABLED,
    language,
    ui,
  });
  const hrWorkflow = useHrWorkflow({
    apiBaseUrl: API_BASE_URL,
    ui,
    enabled: selectedArea === "admin",
  });

  return (
    <main className="min-h-screen flex flex-col items-center p-8 gap-6">
      <AreaLanguageNav
        language={language}
        selectedArea={selectedArea}
        onAreaChange={setSelectedArea}
        onLanguageChange={updateLanguage}
      />

      {selectedArea === "admin" ? (
        <HrSetupPanel state={hrWorkflow} />
      ) : (
        <UserInterviewPanel
          state={userInterview}
          ui={ui}
          presentationModeEnabled={PRESENTATION_MODE_ENABLED}
        />
      )}
    </main>
  );
}
