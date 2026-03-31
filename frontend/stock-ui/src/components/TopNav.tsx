"use client";

import { useRouter } from "next/navigation";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLanguage } from "@/context/LanguageContext";
import { marketLabel, normalizeTicker, tickerDisplayName } from "@/lib/tickerMap";

type Props = {
  inputTicker: string;
  setInputTicker: (value: string) => void;
  active: "research" | "explain" | "watchlist";
};

export function TopNav({ inputTicker, setInputTicker, active }: Props) {
  const router = useRouter();
  const { t } = useLanguage();

  const normalizedTicker = normalizeTicker(inputTicker);
  const detectedMarket = marketLabel(inputTicker);
  const displayName = tickerDisplayName(inputTicker);

  const navBtn = (
    key: "research" | "explain" | "watchlist",
    href: string,
    label: string
  ) => {
    const isActive = active === key;
    return (
      <button
        onClick={() => router.push(href)}
        className={`rounded-xl px-4 py-2 ${
          isActive
            ? "bg-white text-black"
            : "border border-white/10 bg-zinc-900 text-white"
        }`}
      >
        {label}
      </button>
    );
  };
  return (
    <div className="mb-6 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-white">{t.appName}</h1>
        <LanguageToggle />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={inputTicker}
          onChange={(e) => setInputTicker(e.target.value)}
          placeholder={t.searchPlaceholder}
          className="rounded-xl border border-white/10 bg-black px-4 py-2 text-white"
        />

        {normalizedTicker ? (
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-zinc-300">
            <span>{t.canonicalSymbol}: {normalizedTicker}</span>
            {displayName !== normalizedTicker ? <span>• {displayName}</span> : null}
            {detectedMarket ? <span>• {t.market}: {detectedMarket}</span> : null}
          </div>
        ) : null}

        {navBtn(
          "research",
          `/copilot?mode=research&ticker=${encodeURIComponent(normalizedTicker)}`,
          t.research
        )}

        {navBtn(
          "explain",
          `/copilot?mode=explain&ticker=${encodeURIComponent(normalizedTicker)}`,
          t.explain
        )}

        {navBtn("watchlist", "/watchlist", t.watchlist)}
      </div>
    </div>
  );
}
