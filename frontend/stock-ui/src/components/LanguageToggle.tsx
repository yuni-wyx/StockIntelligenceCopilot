"use client";

import { useLanguage } from "@/context/LanguageContext";

export function LanguageToggle() {
  const { locale, setLocale } = useLanguage();

  return (
    <div className="inline-flex rounded-xl border border-white/10 bg-zinc-900 p-1">
      <button
        onClick={() => setLocale("en")}
        className={`rounded-lg px-3 py-1.5 text-sm ${
          locale === "en" ? "bg-white text-black" : "text-white"
        }`}
      >
        EN
      </button>
      <button
        onClick={() => setLocale("zh")}
        className={`rounded-lg px-3 py-1.5 text-sm ${
          locale === "zh" ? "bg-white text-black" : "text-white"
        }`}
      >
        中文
      </button>
    </div>
  );
}