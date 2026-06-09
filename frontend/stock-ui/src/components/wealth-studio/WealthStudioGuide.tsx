"use client";

import type { WealthStudioCopy } from "@/i18n/messages";

export function WealthStudioGuide({ copy }: { copy: WealthStudioCopy }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/50 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{copy.firstRunTitle}</h2>
          <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.firstRunHelper}</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {copy.firstRunSteps.map((step, index) => (
            <div key={step} className="rounded-xl border border-white/10 bg-black/25 p-3">
              <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
                {copy.firstRunStepLabel} {index + 1}
              </div>
              <div className="mt-1 text-sm font-medium text-zinc-100">{step}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
