import { useSyncExternalStore } from "react";
import {
  LANGUAGE_STORAGE_KEY,
  type LanguageCode,
} from "../lib/translations";

const DEFAULT_LANGUAGE: LanguageCode = "en";
const LANGUAGE_CHANGE_EVENT = "prepper-language-change";

function readStoredLanguage(): LanguageCode {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return storedLanguage === "en"
    || storedLanguage === "de"
    || storedLanguage === "fr"
    ? storedLanguage
    : DEFAULT_LANGUAGE;
}

function subscribeLanguageChange(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleChange = () => onStoreChange();
  window.addEventListener("storage", handleChange);
  window.addEventListener(LANGUAGE_CHANGE_EVENT, handleChange);

  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(LANGUAGE_CHANGE_EVENT, handleChange);
  };
}

export function useLanguage() {
  const language = useSyncExternalStore(
    subscribeLanguageChange,
    readStoredLanguage,
    () => DEFAULT_LANGUAGE,
  );

  const updateLanguage = (nextLanguage: LanguageCode) => {
    if (typeof window === "undefined") {
      return;
    }

    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    window.dispatchEvent(new Event(LANGUAGE_CHANGE_EVENT));
  };

  return { language, updateLanguage };
}
