export type LanguageCode = "en" | "de";

export const LANGUAGE_STORAGE_KEY = "prepper-language";

export const LANGUAGE_DISPLAY: Record<
  LanguageCode,
  { flag: string; label: string }
> = {
  en: { flag: "🇬🇧", label: "English" },
  de: { flag: "🇩🇪", label: "Deutsch" },
};

type TranslationStrings = {
  appTitle: string;
  appSubtitle: string;
  promptLabel: string;
  promptLoading: string;
  promptUnavailable: string;
  promptLockedHint: string;
  settingsLabel: string;
  advancedSettingsLabel: string;
  advancedSettingsHint: string;
  temperatureLabel: string;
  topPLabel: string;
  frequencyPenaltyLabel: string;
  presencePenaltyLabel: string;
  conversationEmpty: string;
  thinking: string;
  inputPlaceholderStarted: string;
  inputPlaceholderNotStarted: string;
  startInterview: string;
  starting: string;
  resetConversation: string;
  send: string;
  errorLoadPrompts: string;
  errorFallback: string;
  errorBackendUnavailable: string;
  questionLimitLabel: string;
  questionLimitHint: string;
  difficultyLabel: string;
  difficultyHint: string;
  difficultyJunior: string;
  difficultySenior: string;
  difficultyPrincipal: string;
  interviewComplete: string;
  scoreLabel: string;
  passLabel: string;
  failLabel: string;
  strengthsLabel: string;
  improvementsLabel: string;
  rubricLabel: string;
  interviewLockedPlaceholder: string;
};

export const TRANSLATIONS: Record<LanguageCode, TranslationStrings> = {
  en: {
    appTitle: "Prepper",
    appSubtitle: "Interview preparation, powered by AI.",
    promptLabel: "Interview type",
    promptLoading: "Loading prompts...",
    promptUnavailable: "Prompt list unavailable",
    promptLockedHint: "Reset the conversation to choose a different interview.",
    settingsLabel: "Settings",
    advancedSettingsLabel: "Advanced Settings",
    advancedSettingsHint:
      "These controls override the selected prompt defaults for this interview run.",
    temperatureLabel: "Temperature",
    topPLabel: "Top P",
    frequencyPenaltyLabel: "Frequency penalty",
    presencePenaltyLabel: "Presence penalty",
    conversationEmpty:
      "Choose an interview type, then start the interview to receive the first question.",
    thinking: "Thinking...",
    inputPlaceholderStarted: "Respond to the interviewer...",
    inputPlaceholderNotStarted:
      "Choose an interview and start to enable your response box...",
    startInterview: "Start interview",
    starting: "Starting...",
    resetConversation: "Reset conversation",
    send: "Send",
    errorLoadPrompts: "Could not load system prompts.",
    errorFallback: "Something went wrong.",
    errorBackendUnavailable: "Could not reach the backend.",
    questionLimitLabel: "Scored question limit",
    questionLimitHint:
      "Only new interviewer questions count. Clarifications do not.",
    difficultyLabel: "Interview level",
    difficultyHint:
      "Junior = easier scope and more hints. Principal = deeper ambiguity and stricter evaluation.",
    difficultyJunior: "Junior",
    difficultySenior: "Senior",
    difficultyPrincipal: "Principal",
    interviewComplete: "Interview complete",
    scoreLabel: "Overall score",
    passLabel: "Pass",
    failLabel: "Fail",
    strengthsLabel: "Strengths",
    improvementsLabel: "Improvements",
    rubricLabel: "Rubric scores",
    interviewLockedPlaceholder:
      "Interview completed. Reset the conversation to start a new run.",
  },
  de: {
    appTitle: "Prepper",
    appSubtitle: "Interviewvorbereitung mit KI-Unterstuetzung.",
    promptLabel: "Interviewtyp",
    promptLoading: "Prompts werden geladen...",
    promptUnavailable: "Prompt-Liste nicht verfuegbar",
    promptLockedHint:
      "Setze das Gespraech zurueck, um ein anderes Interview zu waehlen.",
    settingsLabel: "Einstellungen",
    advancedSettingsLabel: "Erweiterte Einstellungen",
    advancedSettingsHint:
      "Diese Regler ueberschreiben die Standardwerte des ausgewaehlten Prompts fuer diesen Durchlauf.",
    temperatureLabel: "Temperature",
    topPLabel: "Top P",
    frequencyPenaltyLabel: "Frequency Penalty",
    presencePenaltyLabel: "Presence Penalty",
    conversationEmpty:
      "Waehle zuerst einen Interviewtyp und starte dann das Interview, um die erste Frage zu erhalten.",
    thinking: "Denke nach...",
    inputPlaceholderStarted:
      "Antworte der Interviewerin oder dem Interviewer...",
    inputPlaceholderNotStarted:
      "Waehle ein Interview und starte es, um das Antwortfeld zu aktivieren...",
    startInterview: "Interview starten",
    starting: "Startet...",
    resetConversation: "Gespraech zuruecksetzen",
    send: "Senden",
    errorLoadPrompts: "System-Prompts konnten nicht geladen werden.",
    errorFallback: "Etwas ist schiefgelaufen.",
    errorBackendUnavailable: "Backend konnte nicht erreicht werden.",
    questionLimitLabel: "Limit fuer bewertete Fragen",
    questionLimitHint:
      "Nur neue Interviewfragen zaehlen. Rueckfragen zaehlen nicht.",
    difficultyLabel: "Interview-Level",
    difficultyHint:
      "Junior = klarer Umfang und mehr Hinweise. Principal = mehr Ambiguitaet und strengere Bewertung.",
    difficultyJunior: "Junior",
    difficultySenior: "Senior",
    difficultyPrincipal: "Principal",
    interviewComplete: "Interview abgeschlossen",
    scoreLabel: "Gesamtpunktzahl",
    passLabel: "Bestanden",
    failLabel: "Nicht bestanden",
    strengthsLabel: "Staerken",
    improvementsLabel: "Verbesserungen",
    rubricLabel: "Rubrik-Bewertungen",
    interviewLockedPlaceholder:
      "Interview ist abgeschlossen. Setze das Gespraech zurueck, um neu zu starten.",
  },
};
