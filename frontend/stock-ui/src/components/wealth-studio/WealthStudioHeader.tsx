"use client";

import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import type { WealthStudioCopy } from "@/i18n/messages";
import { secondaryLinkClassName } from "./shared";

export function WealthStudioHeader({ copy }: { copy: WealthStudioCopy }) {
  return (
    <header className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-zinc-900/60 p-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        <p className="text-xs font-medium uppercase tracking-[0.22em] text-amber-200/70">
          {copy.eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {copy.title}
        </h1>
        <p className="mt-3 text-sm leading-6 text-zinc-300">{copy.subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <LanguageToggle />
        <Link href="/" className={secondaryLinkClassName}>
          {copy.home}
        </Link>
        <Link href="/copilot?mode=research" className={secondaryLinkClassName}>
          {copy.researchMode}
        </Link>
      </div>
    </header>
  );
}
