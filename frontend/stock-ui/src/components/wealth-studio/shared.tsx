"use client";

import type { ReactNode } from "react";

export const inputClassName =
  "min-h-11 w-full min-w-0 rounded-xl border border-white/10 bg-black/45 px-3 py-2 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50";

export const invalidInputClassName =
  "min-h-11 w-full min-w-0 rounded-xl border border-amber-300/60 bg-amber-300/10 px-3 py-2 text-sm text-white outline-none transition placeholder:text-amber-100/40 focus:border-amber-200";

export const textareaClassName =
  "min-h-36 w-full min-w-0 resize-y rounded-xl border border-white/10 bg-black/45 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50";

export const secondaryLinkClassName =
  "rounded-xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-zinc-200 transition hover:border-white/20";

export const primaryButtonClassName =
  "w-full rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50 sm:w-auto";

export const secondaryButtonClassName =
  "w-full rounded-xl border border-white/10 bg-black/25 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-white/20 hover:bg-black/35 disabled:opacity-50 sm:w-auto";

export function SectionIntro({
  title,
  helper,
}: {
  title: string;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/50 p-5">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">{helper}</p>
    </div>
  );
}

export function Field({
  label,
  children,
  helper,
  className = "",
}: {
  label: string;
  children: ReactNode;
  helper?: string;
  className?: string;
}) {
  return (
    <label className={`block min-w-0 text-sm ${className}`}>
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </span>
      {children}
      {helper ? (
        <span className="mt-1.5 block text-xs leading-5 text-zinc-600">{helper}</span>
      ) : null}
    </label>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-4 rounded-2xl border border-dashed border-white/10 bg-black/20 p-5">
      <h3 className="font-medium text-zinc-200">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{body}</p>
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "good" | "warning" | "danger" | "neutral";
}) {
  const toneClass = {
    good: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
    warning: "border-amber-300/30 bg-amber-300/10 text-amber-100",
    danger: "border-rose-300/30 bg-rose-300/10 text-rose-100",
    neutral: "border-white/10 bg-white/10 text-zinc-200",
  }[tone];

  return (
    <span className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-medium ${toneClass}`}>
      {children}
    </span>
  );
}

export function InsightPanel({
  title,
  helper,
  badge,
  children,
}: {
  title: string;
  helper: string;
  badge?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-zinc-400">{helper}</p>
        </div>
        {badge}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

export function InsightStat({
  label,
  value,
  helper,
  suffix = "",
  displayValue,
}: {
  label: string;
  value: number | null | undefined;
  helper: string;
  suffix?: string;
  displayValue?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="mt-2 break-words text-2xl font-semibold tabular-nums">
        {displayValue ?? formatNumber(value)}
        {displayValue ? "" : suffix}
      </div>
      <p className="mt-2 text-xs leading-5 text-zinc-500">{helper}</p>
    </div>
  );
}

export function MiniMetric({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 break-words text-sm font-medium tabular-nums text-zinc-200">
        {formatNumber(value)}
        {suffix}
      </div>
    </div>
  );
}

export function SnapshotRow({ label, level }: { label: string; level: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-zinc-300">{label}</span>
        <Badge tone="neutral">{level}</Badge>
      </div>
    </div>
  );
}

export function ListContent({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm leading-6 text-zinc-400">{emptyLabel}</p>;
  }

  return (
    <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
      {items.map((item) => (
        <li key={item} className="break-words">
          {item}
        </li>
      ))}
    </ul>
  );
}

export function MetricCard({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="mt-2 break-words text-2xl font-semibold tabular-nums">
        {formatNumber(value)}
        {suffix}
      </div>
    </div>
  );
}

export function ExposureCard({
  title,
  items,
  copy,
}: {
  title: string;
  items: Record<string, number>;
  copy: {
    noExposure: string;
    showMore: string;
    more: string;
  };
}) {
  const entries = Object.entries(items).sort(([, a], [, b]) => b - a);
  const primaryEntries = entries.slice(0, 3);
  const remainingEntries = entries.slice(3);

  const renderExposure = ([label, pct]: [string, number]) => (
    <div key={label}>
      <div className="flex items-center justify-between text-sm">
        <span className="min-w-0 break-words pr-3">{label}</span>
        <span>{pct.toFixed(2)}%</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-white/10">
        <div
          className="h-2 rounded-full bg-white"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-4 space-y-3">
        {entries.length === 0 ? (
          <p className="text-sm text-zinc-400">{copy.noExposure}</p>
        ) : (
          <>
            {primaryEntries.map(renderExposure)}
            {remainingEntries.length > 0 ? (
              <details className="pt-1">
                <summary className="cursor-pointer text-xs text-zinc-500">
                  {copy.showMore} {remainingEntries.length} {copy.more}
                </summary>
                <div className="mt-3 space-y-3">
                  {remainingEntries.map(renderExposure)}
                </div>
              </details>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

export function ListCard({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-400">{emptyLabel}</p>
      ) : (
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
          {items.map((item) => (
            <li key={item} className="break-words">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function InfoPanel({
  title,
  helper,
  badge,
  body,
  children,
}: {
  title: string;
  helper?: string;
  badge?: ReactNode;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="font-semibold">{title}</h3>
          {helper ? (
            <p className="mt-1 text-sm leading-6 text-zinc-400">{helper}</p>
          ) : null}
        </div>
        {badge}
      </div>
      {children ? (
        <div className="mt-4">{children}</div>
      ) : body ? (
        <p className="mt-3 text-sm leading-6 text-zinc-300">{body}</p>
      ) : null}
    </div>
  );
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
}

export function qualitativeTone(
  value: number | null | undefined,
): "good" | "warning" | "danger" | "neutral" {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "neutral";
  }
  if (value >= 75) return "good";
  if (value >= 50) return "warning";
  return "danger";
}

export function qualitativeLevel(
  value: number | null | undefined,
  copy: {
    low: string;
    moderate: string;
    high: string;
    notScored: string;
  },
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return copy.notScored;
  }
  if (value >= 75) return copy.high;
  if (value >= 50) return copy.moderate;
  return copy.low;
}

export function concentrationLevel(
  value: number | null | undefined,
  copy: {
    low: string;
    moderate: string;
    high: string;
    notScored: string;
  },
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return copy.notScored;
  }
  if (value >= 75) return copy.low;
  if (value >= 50) return copy.moderate;
  return copy.high;
}
