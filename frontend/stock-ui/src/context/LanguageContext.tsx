"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { Locale, messages } from "@/i18n/messages";

type MessageCatalog = (typeof messages)[Locale];

type LanguageContextType = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: MessageCatalog;
};

const LanguageContext = createContext<LanguageContextType | null>(null);

const STORAGE_KEY = "stock-copilot-locale";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === "undefined") {
      return "en";
    }
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved === "en" || saved === "zh" ? saved : "en";
  });

  const setLocale = (nextLocale: Locale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem(STORAGE_KEY, nextLocale);
  };

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: messages[locale],
    }),
    [locale]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return ctx;
}
