"use client";

import type { WealthStudioCopy } from "@/i18n/messages";
import { EmptyState } from "./shared";

type Props = {
  copy: WealthStudioCopy;
  savedPortfolios: Array<Record<string, unknown>>;
};

export function SavedWorkspacesPanel({ copy, savedPortfolios }: Props) {
  return (
    <details className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
      <summary className="cursor-pointer text-xl font-semibold text-white">
        {copy.savedWorkspaces}
      </summary>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{copy.savedWorkspacesHelper}</p>
      {savedPortfolios.length > 0 ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {savedPortfolios.map((portfolio) => (
            <div
              key={String(portfolio.name)}
              className="rounded-2xl border border-white/10 bg-black/30 p-4 text-sm"
            >
              <div className="break-words font-medium">{String(portfolio.name)}</div>
              <div className="mt-2 text-zinc-400">
                {copy.holdingsCount}: {String(portfolio.holding_count ?? 0)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title={copy.noSavedTitle} body={copy.noSavedBody} />
      )}
    </details>
  );
}
