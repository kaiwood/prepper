"use client";

import { useState } from "react";
import AreaLanguageNav from "../components/AreaLanguageNav";
import DashboardPanel from "../components/DashboardPanel";
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

type Area = "user" | "admin" | "dashboard";

export default function Home() {
  const [selectedArea, setSelectedArea] = useState<Area>("user");
  const { language, updateLanguage } = useLanguage();
  const ui = TRANSLATIONS[language];
  const userInterview = useUserInterview({
    apiBaseUrl: API_BASE_URL,
    presentationModeEnabled: PRESENTATION_MODE_ENABLED,
    language,
    ui,
    active: selectedArea === "user",
  });
  const hrWorkflow = useHrWorkflow({
    apiBaseUrl: API_BASE_URL,
    presentationModeEnabled: PRESENTATION_MODE_ENABLED,
    language,
    ui,
    enabled: selectedArea === "admin",
  });

  const handleClearAllData = () => {
    userInterview.handleClearAll();
    void hrWorkflow.handleClearAllData();
  };

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-950">
      <AreaLanguageNav
        language={language}
        selectedArea={selectedArea}
        onAreaChange={setSelectedArea}
        onLanguageChange={updateLanguage}
        ui={ui}
      />

      <div className="mx-auto w-full max-w-[1480px] px-4 py-6 sm:px-8">
        {selectedArea === "admin" ? (
          <HrSetupPanel
            state={hrWorkflow}
            ui={ui}
            onClearAllData={handleClearAllData}
          />
        ) : selectedArea === "dashboard" ? (
          <DashboardPanel apiBaseUrl={API_BASE_URL} ui={ui} />
        ) : (
          <UserInterviewPanel
            state={userInterview}
            ui={ui}
            presentationModeEnabled={PRESENTATION_MODE_ENABLED}
            onEditContext={() => setSelectedArea("admin")}
          />
        )}
      </div>
    </main>
  );
}
