"use client";

import type { PortfolioChatResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import {
  Badge,
  Field,
  InfoPanel,
  ListContent,
  primaryButtonClassName,
  textareaClassName,
} from "./shared";
import type { PortfolioChatQuestionChip } from "./types";

type Props = {
  copy: WealthStudioCopy;
  loading: boolean;
  question: string;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
  onAskQuestion: (value: string) => void;
  response: PortfolioChatResponse | null;
  starterQuestions: PortfolioChatQuestionChip[];
};

export function PortfolioCoachPanel({
  copy,
  loading,
  question,
  onQuestionChange,
  onAsk,
  onAskQuestion,
  response,
  starterQuestions,
}: Props) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200/60">
            {copy.ideasSection}
          </div>
          <h2 className="mt-1 text-xl font-semibold">{copy.askAboutMyPortfolio}</h2>
        </div>
        <Badge tone="neutral">{copy.portfolioChatContextNote}</Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{copy.portfolioChatHelper}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {starterQuestions.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onAskQuestion(item.label)}
            className="rounded-full border border-white/10 bg-black/25 px-3 py-1.5 text-sm text-zinc-200 transition hover:border-white/20 hover:bg-black/35"
          >
            {item.label}
          </button>
        ))}
      </div>

      <Field label={copy.question} className="mt-4">
        <textarea
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          rows={6}
          placeholder={copy.portfolioChatPlaceholder}
          className={textareaClassName}
        />
      </Field>

      <button
        onClick={onAsk}
        disabled={loading}
        className={`mt-4 ${primaryButtonClassName}`}
      >
        {copy.askAboutPortfolioCta}
      </button>

      {response ? (
        <div className="mt-5 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
              {copy.askAboutMyPortfolio}
            </div>
            <p className="mt-2 whitespace-pre-line text-sm leading-6 text-zinc-200">
              {response.answer}
            </p>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <InfoPanel
              title={copy.concentrationAnalysis}
              helper={copy.portfolioChatConcentrationHelper}
              badge={<Badge tone="warning">{copy.reviewContext}</Badge>}
            >
              <p className="text-sm leading-6 text-zinc-300">
                {response.portfolio_context.concentration_summary}
              </p>
            </InfoPanel>
            <InfoPanel
              title={copy.incomeQuality}
              helper={copy.portfolioChatIncomeHelper}
              badge={<Badge tone="neutral">{copy.estimateLabel}</Badge>}
            >
              <p className="text-sm leading-6 text-zinc-300">
                {response.portfolio_context.income_summary}
              </p>
            </InfoPanel>
          </div>

          <InfoPanel
            title={copy.recommendedNextSteps}
            helper={copy.nextStepsHelper}
            badge={<Badge tone="neutral">{copy.reviewContext}</Badge>}
          >
            <ListContent
              items={response.portfolio_context.suggested_review_items.map(
                (item) => `${item.title}: ${item.reason}`,
              )}
              emptyLabel={copy.noReviewItems}
            />
          </InfoPanel>

          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="text-sm font-semibold text-zinc-100">
              {copy.portfolioChatSuggestedFollowups}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {response.suggested_followups.length > 0 ? (
                response.suggested_followups.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => onAskQuestion(item)}
                    className="rounded-full border border-white/10 bg-black/25 px-3 py-1.5 text-sm text-zinc-200 transition hover:border-white/20 hover:bg-black/35"
                  >
                    {item}
                  </button>
                ))
              ) : (
                <p className="text-sm leading-6 text-zinc-400">{copy.portfolioChatNoFollowups}</p>
              )}
            </div>
          </div>

          <details className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
              {copy.portfolioChatEvidenceUsed}
            </summary>
            <div className="mt-3 flex flex-wrap gap-2">
              {response.evidence_used.map((item) => (
                <Badge key={item} tone="neutral">
                  {item}
                </Badge>
              ))}
            </div>
          </details>

          <div className="rounded-2xl border border-amber-300/20 bg-amber-300/5 p-4">
            <div className="text-sm font-semibold text-amber-100">{copy.portfolioChatSafety}</div>
            <p className="mt-2 text-sm leading-6 text-amber-50/90">
              {response.safety_disclaimer}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
