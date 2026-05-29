export type LanguageCode = "en" | "de" | "fr";

export const LANGUAGE_STORAGE_KEY = "prepper-language";

export const LANGUAGE_DISPLAY: Record<
  LanguageCode,
  { flag: string; label: string }
> = {
  en: { flag: "🇬🇧", label: "English" },
  de: { flag: "🇩🇪", label: "Deutsch" },
  fr: { flag: "🇫🇷", label: "Français" },
};

type TranslationStrings = {
  appTitle: string;
  appSubtitle: string;
  navUser: string;
  navAdmin: string;
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
  copyToClipboard: string;
  copyAllMessages: string;
  copiedUserLabel: string;
  copiedAssistantLabel: string;
  inputPlaceholderStarted: string;
  inputPlaceholderNotStarted: string;
  startInterview: string;
  starting: string;
  resetConversation: string;
  generateCandidateAnswer: string;
  generatingCandidateAnswer: string;
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
  notAvailable: string;
  injectionWarning: string;
  interviewLockedPlaceholder: string;
  hrAdminTitle: string;
  hrAdminSubtitle: string;
  hrCompanyUrlLabel: string;
  hrCompanyUrlHint: string;
  hrFetchCompany: string;
  hrFetchingCompany: string;
  hrCompanyTextLabel: string;
  hrCompanyTextPlaceholder: string;
  hrRoleDescriptionLabel: string;
  hrRoleDescriptionPlaceholder: string;
  hrRoleUrlLabel: string;
  hrRoleUrlHint: string;
  hrFetchRole: string;
  hrFetchingRole: string;
  hrResumeTextLabel: string;
  hrResumeTextPlaceholder: string;
  hrResumePdfLabel: string;
  hrResumePdfHint: string;
  hrExtractResumePdf: string;
  hrExtractingResumePdf: string;
  hrProfileUrlLabel: string;
  hrProfileUrlPlaceholder: string;
  hrProfileTokenLabel: string;
  hrProfileTokenPlaceholder: string;
  hrFetchProfile: string;
  hrFetchingProfile: string;
  hrProfileFetchHint: string;
  hrProfileTextLabel: string;
  hrProfileTextPlaceholder: string;
  hrBuildContext: string;
  hrBuildingContext: string;
  hrClearContext: string;
  hrContextSummary: string;
  hrStatusLabel: string;
  hrContextIdLabel: string;
  hrNoContextId: string;
  hrContextRequiredForInterview: string;
  hrCompanyLabel: string;
  hrRoleLabel: string;
  hrCandidateLabel: string;
  hrSourcesLabel: string;
  hrSourceFallback: string;
  hrToolResultsLabel: string;
  hrToolFallback: string;
  hrUnknownStatus: string;
  hrToolCallEventsLabel: string;
  hrContextWarningsLabel: string;
  hrUnknownError: string;
  hrInterviewTitle: string;
  hrInterviewSubtitle: string;
  hrQuestionsLabel: string;
  hrFinalScoreLabel: string;
  hrScoreLabel: string;
  hrPassedLabel: string;
  hrNeedsReviewLabel: string;
  hrInterviewEmpty: string;
  hrPreparingResponse: string;
  hrInterviewCompletePlaceholder: string;
  hrAnswerPlaceholder: string;
  hrStartFirstPlaceholder: string;
  hrStartInterview: string;
  hrStartingInterview: string;
  hrResetInterview: string;
  hrSendAnswer: string;
  hrRetrievedSourcesLabel: string;
  hrActiveToolResultsLabel: string;
  hrValidationCompanyRequired: string;
  hrValidationCompanyEither: string;
  hrValidationRoleRequired: string;
  hrValidationRoleEither: string;
  hrValidationResumeRequired: string;
  hrValidationResumePdfRequired: string;
  hrValidationCompanyUrlLabel: string;
  hrValidationCompanyTextLabel: string;
  hrValidationRoleDescriptionLabel: string;
  hrValidationRoleUrlLabel: string;
  hrValidationResumeTextLabel: string;
  hrValidationProfileTextLabel: string;
  hrValidationTooLong: (label: string, maxLength: number) => string;
};

export const TRANSLATIONS: Record<LanguageCode, TranslationStrings> = {
  en: {
    appTitle: "Prepper",
    appSubtitle: "Interview preparation, powered by AI.",
    navUser: "User",
    navAdmin: "Company",
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
    copyToClipboard: "Copy to clipboard",
    copyAllMessages: "Copy all messages",
    copiedUserLabel: "User",
    copiedAssistantLabel: "Assistant",
    inputPlaceholderStarted: "Respond to the interviewer...",
    inputPlaceholderNotStarted:
      "Choose an interview and start to enable your response box...",
    startInterview: "Start interview",
    starting: "Starting...",
    resetConversation: "Reset conversation",
    generateCandidateAnswer: "Draft",
    generatingCandidateAnswer: "Drafting...",
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
    notAvailable: "Not available",
    interviewLockedPlaceholder:
      "Interview completed. Reset the conversation to start a new run.",
    injectionWarning:
      "This message contains patterns often used in prompt-injection attempts. It will still be sent, but treat results with caution.",
    hrAdminTitle: "Company HR setup",
    hrAdminSubtitle:
      "Build a candidate evaluation context from company, role, resume, and optional profile information.",
    hrCompanyUrlLabel: "Company URL",
    hrCompanyUrlPlaceholder: "Enter a public company URL.",
    hrCompanyUrlHint: "Use either a public company URL or paste company text below.",
    hrFetchCompany: "Fetch company",
    hrFetchingCompany: "Fetching...",
    hrCompanyTextLabel: "Company text",
    hrCompanyTextPlaceholder:
      "Paste company overview, values, and interview-relevant facts.",
    hrRoleDescriptionLabel: "Role description",
    hrRoleDescriptionPlaceholder:
      "Paste responsibilities, required skills, and success signals.",
    hrRoleUrlLabel: "Job-ad URL",
    hrRoleUrlPlaceholder: "Enter a public job-ad URL.",
    hrRoleUrlHint: "Use either a public job-ad URL or paste the role description.",
    hrFetchRole: "Fetch role",
    hrFetchingRole: "Fetching...",
    hrResumeTextLabel: "Resume text",
    hrResumeTextPlaceholder: "Paste candidate resume content.",
    hrResumePdfLabel: "Resume PDF",
    hrResumePdfHint: "Upload a text-based PDF to extract resume text. Files are processed in memory only.",
    hrExtractResumePdf: "Extract PDF text",
    hrExtractingResumePdf: "Extracting...",
    hrProfileUrlLabel: "LinkedIn/Xing URL",
    hrProfileUrlPlaceholder: "Enter a public LinkedIn or Xing profile URL.",
    hrProfileTokenLabel: "OAuth token",
    hrProfileTokenPlaceholder: "Paste a short-lived provider OAuth token.",
    hrFetchProfile: "Fetch profile",
    hrFetchingProfile: "Fetching...",
    hrProfileFetchHint: "Uses the token for this request only. It is not saved.",
    hrProfileTextLabel: "Profile text optional",
    hrProfileTextPlaceholder: "Paste public profile or LinkedIn summary notes.",
    hrBuildContext: "Build context",
    hrBuildingContext: "Building context...",
    hrClearContext: "Clear",
    hrContextSummary: "Context summary",
    hrStatusLabel: "Status",
    hrContextIdLabel: "Context ID",
    hrNoContextId: "No context ID was returned. Review tool errors before continuing.",
    hrContextRequiredForInterview: "Build HR context in Company before starting the candidate-fit interview.",
    hrCompanyLabel: "Company",
    hrRoleLabel: "Role",
    hrCandidateLabel: "Candidate",
    hrSourcesLabel: "Sources",
    hrSourceFallback: "Source",
    hrToolResultsLabel: "Tool results",
    hrToolFallback: "tool",
    hrUnknownStatus: "unknown",
    hrToolCallEventsLabel: "Tool-call events",
    hrContextWarningsLabel: "Context build warnings",
    hrUnknownError: "Unknown error",
    hrInterviewTitle: "HR candidate-fit interview",
    hrInterviewSubtitle:
      "Start a live HR interview using the built company, role, and candidate context.",
    hrQuestionsLabel: "Questions",
    hrFinalScoreLabel: "Final score",
    hrScoreLabel: "Score",
    hrPassedLabel: "Passed",
    hrNeedsReviewLabel: "Needs review",
    hrInterviewEmpty: "Start the HR interview to see candidate-fit questions.",
    hrPreparingResponse: "Preparing HR response...",
    hrInterviewCompletePlaceholder: "The HR interview is complete.",
    hrAnswerPlaceholder: "Type the candidate answer...",
    hrStartFirstPlaceholder: "Start the HR interview first.",
    hrStartInterview: "Start HR interview",
    hrStartingInterview: "Starting HR interview...",
    hrResetInterview: "Reset HR interview",
    hrSendAnswer: "Send answer",
    hrRetrievedSourcesLabel: "Retrieved sources",
    hrActiveToolResultsLabel: "Active tool results",
    hrValidationCompanyRequired: "Enter a company URL or paste company text.",
    hrValidationCompanyEither: "Enter either a company URL or company text, not both.",
    hrValidationRoleRequired: "Enter either a job-ad URL or role description.",
    hrValidationRoleEither: "Enter either a job-ad URL or role description, not both.",
    hrValidationResumeRequired: "Resume text is required.",
    hrValidationResumePdfRequired: "Extract resume PDF text before building context.",
    hrValidationCompanyUrlLabel: "Company URL",
    hrValidationCompanyTextLabel: "Company text",
    hrValidationRoleDescriptionLabel: "Role description",
    hrValidationRoleUrlLabel: "Job-ad URL",
    hrValidationResumeTextLabel: "Resume text",
    hrValidationProfileTextLabel: "Profile text",
    hrValidationTooLong: (label, maxLength) =>
      `${label} must be ${maxLength} characters or fewer.`,
  },
  de: {
    appTitle: "Prepper",
    appSubtitle: "Interviewvorbereitung mit KI-Unterstützung.",
    navUser: "Nutzer",
    navAdmin: "Unternehmen",
    promptLabel: "Interviewtyp",
    promptLoading: "Prompts werden geladen...",
    promptUnavailable: "Prompt-Liste nicht verfügbar",
    promptLockedHint:
      "Setze das Gespräch zurück, um ein anderes Interview zu wählen.",
    settingsLabel: "Einstellungen",
    advancedSettingsLabel: "Erweiterte Einstellungen",
    advancedSettingsHint:
      "Diese Regler überschreiben die Standardwerte des ausgewählten Prompts für diesen Durchlauf.",
    temperatureLabel: "Temperatur",
    topPLabel: "Top P",
    frequencyPenaltyLabel: "Frequenzstrafe",
    presencePenaltyLabel: "Präsenzstrafe",
    conversationEmpty:
      "Wähle zuerst einen Interviewtyp und starte dann das Interview, um die erste Frage zu erhalten.",
    thinking: "Denke nach...",
    copyToClipboard: "In die Zwischenablage kopieren",
    copyAllMessages: "Alle Nachrichten kopieren",
    copiedUserLabel: "Nutzer",
    copiedAssistantLabel: "Assistent",
    inputPlaceholderStarted:
      "Antworte der Interviewerin oder dem Interviewer...",
    inputPlaceholderNotStarted:
      "Wähle ein Interview und starte es, um das Antwortfeld zu aktivieren...",
    startInterview: "Interview starten",
    starting: "Startet...",
    resetConversation: "Gespräch zurücksetzen",
    generateCandidateAnswer: "Entwurf",
    generatingCandidateAnswer: "Entwirft...",
    send: "Senden",
    errorLoadPrompts: "System-Prompts konnten nicht geladen werden.",
    errorFallback: "Etwas ist schiefgelaufen.",
    errorBackendUnavailable: "Backend konnte nicht erreicht werden.",
    questionLimitLabel: "Limit für bewertete Fragen",
    questionLimitHint:
      "Nur neue Interviewfragen zählen. Rückfragen zählen nicht.",
    difficultyLabel: "Interview-Level",
    difficultyHint:
      "Junior = klarer Umfang und mehr Hinweise. Principal = mehr Ambiguität und strengere Bewertung.",
    difficultyJunior: "Junior",
    difficultySenior: "Senior",
    difficultyPrincipal: "Principal",
    interviewComplete: "Interview abgeschlossen",
    scoreLabel: "Gesamtpunktzahl",
    passLabel: "Bestanden",
    failLabel: "Nicht bestanden",
    strengthsLabel: "Stärken",
    improvementsLabel: "Verbesserungen",
    rubricLabel: "Rubrik-Bewertungen",
    notAvailable: "Nicht verfügbar",
    interviewLockedPlaceholder:
      "Interview ist abgeschlossen. Setze das Gespräch zurück, um neu zu starten.",
    injectionWarning:
      "Diese Nachricht enthält Muster, die oft bei Prompt-Injection-Versuchen genutzt werden. Sie wird trotzdem gesendet, aber bewerte die Antwort mit Vorsicht.",
    hrAdminTitle: "Unternehmens-HR-Einrichtung",
    hrAdminSubtitle:
      "Erstelle einen Kontext zur Kandidatenbewertung aus Unternehmen, Rolle, Lebenslauf und optionalen Profilinformationen.",
    hrCompanyUrlLabel: "Unternehmens-URL",
    hrCompanyUrlPlaceholder: "Öffentliche Unternehmens-URL eingeben.",
    hrCompanyUrlHint: "Nutze entweder eine öffentliche Unternehmens-URL oder füge unten Unternehmenstext ein.",
    hrFetchCompany: "Unternehmen abrufen",
    hrFetchingCompany: "Wird abgerufen...",
    hrCompanyTextLabel: "Unternehmenstext",
    hrCompanyTextPlaceholder:
      "Füge Unternehmensüberblick, Werte und interviewrelevante Fakten ein.",
    hrRoleDescriptionLabel: "Rollenbeschreibung",
    hrRoleDescriptionPlaceholder:
      "Füge Aufgaben, erforderliche Fähigkeiten und Erfolgssignale ein.",
    hrRoleUrlLabel: "Stellenanzeigen-URL",
    hrRoleUrlPlaceholder: "Öffentliche Stellenanzeigen-URL eingeben.",
    hrRoleUrlHint: "Nutze entweder eine öffentliche Stellenanzeigen-URL oder füge die Rollenbeschreibung ein.",
    hrFetchRole: "Rolle abrufen",
    hrFetchingRole: "Wird abgerufen...",
    hrResumeTextLabel: "Lebenslauftext",
    hrResumeTextPlaceholder: "Füge den Lebenslauf der Kandidatin oder des Kandidaten ein.",
    hrResumePdfLabel: "Lebenslauf-PDF",
    hrResumePdfHint: "Lade eine textbasierte PDF hoch, um Lebenslauftext zu extrahieren. Dateien werden nur im Arbeitsspeicher verarbeitet.",
    hrExtractResumePdf: "PDF-Text extrahieren",
    hrExtractingResumePdf: "Extrahiere...",
    hrProfileUrlLabel: "LinkedIn/Xing-URL",
    hrProfileUrlPlaceholder: "Öffentliche LinkedIn- oder Xing-Profil-URL eingeben.",
    hrProfileTokenLabel: "OAuth-Token",
    hrProfileTokenPlaceholder: "Kurzlebigen OAuth-Token des Anbieters einfügen.",
    hrFetchProfile: "Profil abrufen",
    hrFetchingProfile: "Wird abgerufen...",
    hrProfileFetchHint: "Der Token wird nur für diese Anfrage verwendet und nicht gespeichert.",
    hrProfileTextLabel: "Profiltext optional",
    hrProfileTextPlaceholder: "Füge öffentliches Profil oder LinkedIn-Zusammenfassung ein.",
    hrBuildContext: "Kontext erstellen",
    hrBuildingContext: "Kontext wird erstellt...",
    hrClearContext: "Leeren",
    hrContextSummary: "Kontextzusammenfassung",
    hrStatusLabel: "Status",
    hrContextIdLabel: "Kontext-ID",
    hrNoContextId: "Es wurde keine Kontext-ID zurückgegeben. Prüfe Tool-Fehler, bevor du fortfährst.",
    hrContextRequiredForInterview: "Erstelle zuerst im Unternehmensbereich den HR-Kontext, bevor du das Candidate-Fit-Interview startest.",
    hrCompanyLabel: "Unternehmen",
    hrRoleLabel: "Rolle",
    hrCandidateLabel: "Kandidat",
    hrSourcesLabel: "Quellen",
    hrSourceFallback: "Quelle",
    hrToolResultsLabel: "Tool-Ergebnisse",
    hrToolFallback: "Tool",
    hrUnknownStatus: "unbekannt",
    hrToolCallEventsLabel: "Tool-Aufrufereignisse",
    hrContextWarningsLabel: "Warnungen beim Kontextaufbau",
    hrUnknownError: "Unbekannter Fehler",
    hrInterviewTitle: "HR-Interview zur Kandidateneignung",
    hrInterviewSubtitle:
      "Starte ein Live-HR-Interview mit dem erstellten Kontext zu Unternehmen, Rolle und Kandidat.",
    hrQuestionsLabel: "Fragen",
    hrFinalScoreLabel: "Endbewertung",
    hrScoreLabel: "Punktzahl",
    hrPassedLabel: "Bestanden",
    hrNeedsReviewLabel: "Prüfung nötig",
    hrInterviewEmpty: "Starte das HR-Interview, um Fragen zur Kandidateneignung zu sehen.",
    hrPreparingResponse: "HR-Antwort wird vorbereitet...",
    hrInterviewCompletePlaceholder: "Das HR-Interview ist abgeschlossen.",
    hrAnswerPlaceholder: "Antwort der Kandidatin oder des Kandidaten eingeben...",
    hrStartFirstPlaceholder: "Starte zuerst das HR-Interview.",
    hrStartInterview: "HR-Interview starten",
    hrStartingInterview: "HR-Interview startet...",
    hrResetInterview: "HR-Interview zurücksetzen",
    hrSendAnswer: "Antwort senden",
    hrRetrievedSourcesLabel: "Abgerufene Quellen",
    hrActiveToolResultsLabel: "Aktive Tool-Ergebnisse",
    hrValidationCompanyRequired: "Gib eine Unternehmens-URL ein oder füge Unternehmenstext ein.",
    hrValidationCompanyEither: "Gib entweder eine Unternehmens-URL oder Unternehmenstext ein, nicht beides.",
    hrValidationRoleRequired: "Gib entweder eine Stellenanzeigen-URL oder eine Rollenbeschreibung ein.",
    hrValidationRoleEither: "Gib entweder eine Stellenanzeigen-URL oder eine Rollenbeschreibung ein, nicht beides.",
    hrValidationResumeRequired: "Lebenslauftext ist erforderlich.",
    hrValidationResumePdfRequired: "Extrahiere vor dem Kontextaufbau Lebenslauf-PDF-Text.",
    hrValidationCompanyUrlLabel: "Unternehmens-URL",
    hrValidationCompanyTextLabel: "Unternehmenstext",
    hrValidationRoleDescriptionLabel: "Rollenbeschreibung",
    hrValidationRoleUrlLabel: "Stellenanzeigen-URL",
    hrValidationResumeTextLabel: "Lebenslauftext",
    hrValidationProfileTextLabel: "Profiltext",
    hrValidationTooLong: (label, maxLength) =>
      `${label} darf höchstens ${maxLength} Zeichen lang sein.`,
  },
  fr: {
    appTitle: "Prepper",
    appSubtitle: "Préparation aux entretiens techniques, avec IA.",
    navUser: "Utilisateur",
    navAdmin: "Entreprise",
    promptLabel: "Type d'entretien",
    promptLoading: "Chargement des prompts...",
    promptUnavailable: "Liste des prompts indisponible",
    promptLockedHint: "Réinitialisez la conversation pour choisir un autre entretien.",
    settingsLabel: "Paramètres",
    advancedSettingsLabel: "Paramètres avancés",
    advancedSettingsHint:
      "Ces contrôles remplacent les paramètres par défaut du prompt sélectionné pour cette session.",
    temperatureLabel: "Température",
    topPLabel: "Top P",
    frequencyPenaltyLabel: "Pénalité de fréquence",
    presencePenaltyLabel: "Pénalité de présence",
    conversationEmpty:
      "Choisissez un type d'entretien, puis démarrez pour recevoir la première question.",
    thinking: "Analyse...",
    copyToClipboard: "Copier dans le presse-papiers",
    copyAllMessages: "Copier tous les messages",
    copiedUserLabel: "Utilisateur",
    copiedAssistantLabel: "Assistant",
    inputPlaceholderStarted: "Répondez à l'intervieweur...",
    inputPlaceholderNotStarted:
      "Choisissez un entretien et démarrez pour activer le champ de réponse...",
    startInterview: "Démarrer l'entretien",
    starting: "Démarrage...",
    resetConversation: "Réinitialiser la conversation",
    generateCandidateAnswer: "Brouillon",
    generatingCandidateAnswer: "Rédaction...",
    send: "Envoyer",
    errorLoadPrompts: "Impossible de charger les prompts système.",
    errorFallback: "Une erreur s'est produite.",
    errorBackendUnavailable: "Impossible de contacter le backend.",
    questionLimitLabel: "Limite de questions évaluées",
    questionLimitHint:
      "Seules les nouvelles questions de l'entretien sont comptées. Les clarifications ne le sont pas.",
    difficultyLabel: "Niveau d'entretien",
    difficultyHint:
      "Junior = champ plus simple et plus d'indices. Principal = ambiguïté plus forte et évaluation plus rigoureuse.",
    difficultyJunior: "Junior",
    difficultySenior: "Senior",
    difficultyPrincipal: "Principal",
    interviewComplete: "Entretien terminé",
    scoreLabel: "Score global",
    passLabel: "Réussi",
    failLabel: "Échoué",
    strengthsLabel: "Points forts",
    improvementsLabel: "Améliorations",
    rubricLabel: "Notes par critères",
    notAvailable: "Non disponible",
    interviewLockedPlaceholder:
      "Entretien terminé. Réinitialisez la conversation pour démarrer un nouveau.",
    injectionWarning:
      "Ce message contient des motifs souvent utilisés pour des tentatives d'injection. Il sera envoyé, mais analysez la réponse avec prudence.",
    hrAdminTitle: "Configuration RH de l’entreprise",
    hrAdminSubtitle:
      "Créez un contexte d'évaluation du candidat à partir de l'entreprise, du rôle, du CV et d'informations de profil optionnelles.",
    hrCompanyUrlLabel: "URL de l'entreprise",
    hrCompanyUrlPlaceholder: "Saisissez une URL publique de l'entreprise.",
    hrCompanyUrlHint: "Utilisez soit une URL publique de l'entreprise, soit le texte de l'entreprise ci-dessous.",
    hrFetchCompany: "Récupérer l'entreprise",
    hrFetchingCompany: "Récupération...",
    hrCompanyTextLabel: "Texte de l'entreprise",
    hrCompanyTextPlaceholder:
      "Collez la présentation de l'entreprise, ses valeurs et les faits utiles pour l'entretien.",
    hrRoleDescriptionLabel: "Description du rôle",
    hrRoleDescriptionPlaceholder:
      "Collez les responsabilités, les compétences requises et les signaux de réussite.",
    hrRoleUrlLabel: "URL de l'offre",
    hrRoleUrlPlaceholder: "Saisissez une URL publique d'offre d'emploi.",
    hrRoleUrlHint: "Utilisez soit une URL publique d'offre d'emploi, soit la description du rôle.",
    hrFetchRole: "Récupérer le rôle",
    hrFetchingRole: "Récupération...",
    hrResumeTextLabel: "Texte du CV",
    hrResumeTextPlaceholder: "Collez le contenu du CV du candidat.",
    hrResumePdfLabel: "PDF du CV",
    hrResumePdfHint: "Importez un PDF textuel pour extraire le texte du CV. Les fichiers sont traités uniquement en mémoire.",
    hrExtractResumePdf: "Extraire le texte PDF",
    hrExtractingResumePdf: "Extraction...",
    hrProfileUrlLabel: "URL LinkedIn/Xing",
    hrProfileUrlPlaceholder: "Saisissez une URL publique de profil LinkedIn ou Xing.",
    hrProfileTokenLabel: "Jeton OAuth",
    hrProfileTokenPlaceholder: "Collez un jeton OAuth fournisseur de courte durée.",
    hrFetchProfile: "Récupérer le profil",
    hrFetchingProfile: "Récupération...",
    hrProfileFetchHint: "Le jeton est utilisé uniquement pour cette requête et n'est pas enregistré.",
    hrProfileTextLabel: "Texte de profil optionnel",
    hrProfileTextPlaceholder: "Collez un profil public ou des notes de résumé LinkedIn.",
    hrBuildContext: "Créer le contexte",
    hrBuildingContext: "Création du contexte...",
    hrClearContext: "Effacer",
    hrContextSummary: "Résumé du contexte",
    hrStatusLabel: "Statut",
    hrContextIdLabel: "ID du contexte",
    hrNoContextId: "Aucun ID de contexte n'a été renvoyé. Vérifiez les erreurs d'outil avant de continuer.",
    hrContextRequiredForInterview: "Créez d'abord le contexte RH dans l'espace Entreprise avant de démarrer l'entretien d'adéquation candidat.",
    hrCompanyLabel: "Entreprise",
    hrRoleLabel: "Rôle",
    hrCandidateLabel: "Candidat",
    hrSourcesLabel: "Sources",
    hrSourceFallback: "Source",
    hrToolResultsLabel: "Résultats des outils",
    hrToolFallback: "outil",
    hrUnknownStatus: "inconnu",
    hrToolCallEventsLabel: "Événements d'appel d'outil",
    hrContextWarningsLabel: "Avertissements de création du contexte",
    hrUnknownError: "Erreur inconnue",
    hrInterviewTitle: "Entretien RH d'adéquation candidat",
    hrInterviewSubtitle:
      "Démarrez un entretien RH en direct avec le contexte créé pour l'entreprise, le rôle et le candidat.",
    hrQuestionsLabel: "Questions",
    hrFinalScoreLabel: "Score final",
    hrScoreLabel: "Score",
    hrPassedLabel: "Réussi",
    hrNeedsReviewLabel: "À examiner",
    hrInterviewEmpty: "Démarrez l'entretien RH pour voir les questions d'adéquation candidat.",
    hrPreparingResponse: "Préparation de la réponse RH...",
    hrInterviewCompletePlaceholder: "L'entretien RH est terminé.",
    hrAnswerPlaceholder: "Saisissez la réponse du candidat...",
    hrStartFirstPlaceholder: "Démarrez d'abord l'entretien RH.",
    hrStartInterview: "Démarrer l'entretien RH",
    hrStartingInterview: "Démarrage de l'entretien RH...",
    hrResetInterview: "Réinitialiser l'entretien RH",
    hrSendAnswer: "Envoyer la réponse",
    hrRetrievedSourcesLabel: "Sources récupérées",
    hrActiveToolResultsLabel: "Résultats d'outils actifs",
    hrValidationCompanyRequired: "Saisissez une URL d'entreprise ou collez le texte de l'entreprise.",
    hrValidationCompanyEither: "Saisissez soit une URL d'entreprise, soit le texte de l'entreprise, pas les deux.",
    hrValidationRoleRequired: "Saisissez soit une URL d'offre d'emploi, soit une description du rôle.",
    hrValidationRoleEither: "Saisissez soit une URL d'offre d'emploi, soit une description du rôle, pas les deux.",
    hrValidationResumeRequired: "Le texte du CV est obligatoire.",
    hrValidationResumePdfRequired: "Extrayez le texte du PDF du CV avant de créer le contexte.",
    hrValidationCompanyUrlLabel: "URL de l'entreprise",
    hrValidationCompanyTextLabel: "Texte de l'entreprise",
    hrValidationRoleDescriptionLabel: "Description du rôle",
    hrValidationRoleUrlLabel: "URL de l'offre",
    hrValidationResumeTextLabel: "Texte du CV",
    hrValidationProfileTextLabel: "Texte de profil",
    hrValidationTooLong: (label, maxLength) =>
      `${label} doit contenir ${maxLength} caractères ou moins.`,
  },
};
