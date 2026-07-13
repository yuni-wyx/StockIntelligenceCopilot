"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Locale, messages } from "@/i18n/messages";

type MessageCatalog = (typeof messages)[Locale];

type LanguageContextType = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: MessageCatalog;
  hydrated: boolean;
};

const LanguageContext = createContext<LanguageContextType | null>(null);

const STORAGE_KEY = "stock-copilot-locale";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;

    queueMicrotask(() => {
      if (cancelled) return;
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "zh") {
        setLocaleState(saved);
      }
      setHydrated(true);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const setLocale = (nextLocale: Locale) => {
    setLocaleState(nextLocale);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, nextLocale);
    }
  };

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: messages[locale],
      hydrated,
    }),
    [hydrated, locale]
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
