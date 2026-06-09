"use client";

import type { PortfolioAgentResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import {
  Field,
  InfoPanel,
  ListCard,
  textareaClassName,
} from "./shared";

type Props = {
  copy: WealthStudioCopy;
  loading: boolean;
  question: string;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
  response: PortfolioAgentResponse | null;
};

export function PortfolioCoachPanel({
  copy,
  loading,
  question,
  onQuestionChange,
  onAsk,
  response,
}: Props) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
      <h2 className="text-xl font-semibold">{copy.aiPortfolioCoach}</h2>
      <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.coachHelper}</p>

      <Field label={copy.question} className="mt-4">
        <textarea
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          rows={6}
          placeholder="Should I sell part of 00878 and buy Allianz Taiwan Technology Fund?"
          className={textareaClassName}
        />
      </Field>

      <button
        onClick={onAsk}
        disabled={loading}
        className="mt-4 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
      >
        {copy.askCoach}
      </button>

      {response ? (
        <div className="mt-5 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
              {copy.aiCoach}
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-200">{response.conclusion}</p>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              {response.current_portfolio_diagnosis}
            </p>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ListCard
              title={copy.coachActions}
              items={response.suggested_next_actions}
              emptyLabel={copy.noCoachActions}
            />
            <ListCard title={copy.coachRisks} items={response.risks} emptyLabel={copy.noCoachRisks} />
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <InfoPanel title={copy.bullCase} body={response.bull_case} />
            <InfoPanel title={copy.bearCase} body={response.bear_case} />
            <InfoPanel title={copy.baseCase} body={response.base_case} />
          </div>
        </div>
      ) : null}
    </section>
  );
}
