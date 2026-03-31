"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { detectTickerMarket, normalizeTicker } from "@/lib/tickerMap";

export default function HomePage() {
  const [ticker, setTicker] = useState("");
  const router = useRouter();
  const normalizedTicker = normalizeTicker(ticker);
  const market = detectTickerMarket(ticker);

  const handleEnter = () => {
    const cleanTicker = normalizedTicker;
    if (!cleanTicker) return;
    router.push(`/copilot?mode=trade&ticker=${encodeURIComponent(cleanTicker)}`);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center px-4">
      <button
        onClick={() => router.push("/")}
        className="text-3xl font-bold hover:opacity-80 transition"
      >
        Stock Intelligence Copilot
      </button>

      <p className="mt-2 text-zinc-400">Understand stocks faster across US and Taiwan equities.</p>

      <div className="mt-6 flex gap-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleEnter();
            }
          }}
          placeholder="Enter ticker or company (NVDA, 2330, 2330.TW, 台積電...)"
          className="px-4 py-2 rounded-xl bg-black border border-white/10"
        />

        <button
          onClick={handleEnter}
          className="px-4 py-2 rounded-xl bg-white text-black"
        >
          Open Copilot
        </button>
      </div>

      {normalizedTicker ? (
        <div className="mt-3 text-sm text-zinc-400">
          Canonical symbol: <span className="text-white">{normalizedTicker}</span>
          {market ? <span> • Market: {market}</span> : null}
        </div>
      ) : null}
    </div>
  );
}
