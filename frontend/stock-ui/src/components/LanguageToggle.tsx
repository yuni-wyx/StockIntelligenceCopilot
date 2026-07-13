"use client";

import { useLanguage } from "@/context/LanguageContext";

export function LanguageToggle() {
  const { hydrated, locale, setLocale } = useLanguage();

  return (
    <div className="inline-flex rounded-xl border border-white/10 bg-zinc-900 p-1">
      <button
        type="button"
        onClick={() => setLocale("en")}
        disabled={!hydrated}
        className={`rounded-lg px-3 py-1.5 text-sm ${
          locale === "en" ? "bg-white text-black" : "text-white"
        } disabled:cursor-not-allowed disabled:opacity-60`}
      >
        English
      </button>
      <button
        type="button"
        onClick={() => setLocale("zh")}
        disabled={!hydrated}
        className={`rounded-lg px-3 py-1.5 text-sm ${
          locale === "zh" ? "bg-white text-black" : "text-white"
        } disabled:cursor-not-allowed disabled:opacity-60`}
      >
        繁體中文
      </button>
    </div>
  );
}
