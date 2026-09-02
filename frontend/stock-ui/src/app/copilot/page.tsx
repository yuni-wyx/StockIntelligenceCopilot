"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SignalPanel } from "@/components/copilot/SignalPanel";
import { SignalPayload, extractSignalViewModel } from "@/components/copilot/signal";
import { useLanguage } from "@/context/LanguageContext";
import { buildApiUrl } from "@/lib/apiBase";
import { detectTickerMarket, normalizeTicker } from "@/lib/tickerMap";

type Mode = "trade" | "research" | "explain";
type EventRecord = {
  type: string;
  stage?: string;
  message?: string;
  data?: unknown;
  elapsed?: number;
  step?: string;
  title?: string;
  status?: string;
  summary?: string;
  timestamp?: string;
  latency_ms?: number;
  metadata?: Record<string, unknown>;
};

type TimelineStepKey =
  | "query_interpretation"
  | "planning"
  | "evidence_retrieval"
  | "synthesis"
  | "final_answer";

type TimelineItem = {
  step: TimelineStepKey | string;
  title: string;
  status: string;
  summary: string;
  timestamp?: string;
  latency_ms?: number;
  metadata?: Record<string, unknown>;
};

type CopilotOutput = {
  bias?: string;
  confidence?: number;
  buy_zone?: string;
  stop_loss?: string;
  take_profit?: string;
  reasoning?: string[];
  fundamental_summary?: string;
  recent_news_summary?: string;
  bull_case?: string;
  bear_case?: string;
  price_move_summary?: string;
  overall_confidence?: number;
  ticker?: string;
  signal?: SignalPayload;
  price_change_pct?: number;
  ranked_causes?: Array<{
    rank?: number;
    cause?: string;
    confidence?: number;
    explanation?: string;
  }>;
  error?: string;
  evidence_provenance?: Array<{
    source_id: string;
    source_type: string;
    ticker?: string | null;
    provider?: string | null;
    title?: string | null;
    url?: string | null;
    confidence?: number;
    data_as_of?: string | null;
    freshness?: string | null;
    source_tier?: string | null;
  }>;
  claim_evidence?: Array<{
    claim_id: string;
    output_field: string;
    claim: string;
    evidence_ids: string[];
    confidence_score: number;
    confidence_label: string;
    unsupported: boolean;
    notes: string[];
  }>;
  unsupported_claims?: Array<{
    output_field: string;
    claim: string;
    reason: string;
    severity: string;
  }>;
  confidence_score?: number;
  research_data_gaps?: string[];
  research_conflicts?: string[];
  research_conflict_details?: Array<{
    message: string;
    metric: string;
    severity: string;
  }>;
  volume_context?: string;
};

export default function CopilotPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0a0a0a] text-white px-6 py-6">Loading copilot...</div>}>
      <CopilotPageContent />
    </Suspense>
  );
}

function EvidenceAudit({ output }: { output: CopilotOutput }) {
  const sources = output.evidence_provenance ?? [];
  const claims = output.claim_evidence ?? [];
  const unsupported = output.unsupported_claims ?? [];
  const filingSources = sources.filter((source) => source.source_type === "filing");
  const filingSourceIds = new Set(filingSources.map((source) => source.source_id));
  const filingClaims = claims.filter((claim) =>
    claim.evidence_ids.some((sourceId) => filingSourceIds.has(sourceId)),
  );
  const researchConflicts = output.research_conflicts ?? [];
  const researchDataGaps = output.research_data_gaps ?? [];
  const researchConflictDetails = output.research_conflict_details ?? [];

  if (sources.length === 0 && claims.length === 0 && unsupported.length === 0) {
    return null;
  }

  return (
    <details className="mt-5 rounded-xl border border-white/10 bg-black/25 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
        Evidence provenance
      </summary>
      <p className="mt-2 text-xs leading-5 text-zinc-500">
        Generated insights are linked to available market data, fundamentals,
        analyst signals, news, and deterministic calculations.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <AuditMetric label="Sources" value={sources.length} />
        <AuditMetric label="Linked claims" value={claims.length} />
        <AuditMetric
          label="Confidence"
          value={output.confidence_score !== undefined ? `${Math.round(output.confidence_score * 100)}%` : "N/A"}
        />
      </div>
      {filingSources.length > 0 ? (
        <div className="mt-3 rounded-lg border border-sky-300/20 bg-sky-300/10 p-3">
          <div className="text-xs font-medium text-sky-100">Primary filings</div>
          <p className="mt-1 text-xs leading-5 text-sky-100/70">
            Tier 1 filing sources linked to {filingClaims.length} generated claim(s).
          </p>
          <div className="mt-2 space-y-2">
            {filingSources.map((source) => (
              <div key={source.source_id} className="text-xs text-sky-50">
                <span className="font-medium">{source.provider || "SEC filing"}</span>
                {source.ticker ? ` · ${source.ticker}` : ""}
                {source.data_as_of || source.freshness ? (
                  <div className="mt-1 text-sky-100/70">
                    {source.freshness || "Source date"}
                    {source.data_as_of ? ` · As of ${source.data_as_of.slice(0, 10)}` : ""}
                  </div>
                ) : null}
                {source.url ? (
                  <a href={source.url} target="_blank" rel="noreferrer" className="ml-2 break-all text-amber-100 hover:text-white">
                    Open filing
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {researchConflicts.length > 0 || researchDataGaps.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-300/25 bg-amber-300/10 p-3">
          <div className="text-xs font-medium text-amber-100">Research data quality notes</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-100/80">
            {[...researchConflictDetails.map((item) => `${item.severity.toUpperCase()}: ${item.message}`), ...researchConflicts, ...researchDataGaps].slice(0, 4).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {unsupported.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-300/25 bg-amber-300/10 p-3">
          <div className="text-xs font-medium text-amber-100">Unsupported claim warnings</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-100/80">
            {unsupported.slice(0, 4).map((item) => (
              <li key={`${item.output_field}-${item.reason}`}>
                {item.output_field}: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="mt-3 space-y-2">
        {sources.slice(0, 5).map((source) => (
          <div key={source.source_id} className="rounded-lg border border-white/10 bg-black/20 p-2 text-xs">
            <div className="font-medium text-zinc-200">
              {source.source_type}
              {source.ticker ? ` · ${source.ticker}` : ""}
            </div>
            <div className="mt-1 break-words text-zinc-500">
              {source.title || source.provider || source.source_id}
            </div>
            {source.data_as_of || source.freshness ? (
              <div className="mt-1 text-zinc-600">
                {source.freshness || "Source date"}{source.data_as_of ? ` · As of ${source.data_as_of.slice(0, 10)}` : ""}
              </div>
            ) : null}
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-block break-all text-amber-100 hover:text-white"
              >
                {source.url}
              </a>
            ) : null}
          </div>
        ))}
      </div>
    </details>
  );
}

function AuditMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-2">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-zinc-100">{value}</div>
    </div>
  );
}

function CopilotPageContent() {
  const searchParams = useSearchParams();
  const initialTicker = normalizeTicker(searchParams.get("ticker") ?? "");
  const requestedMode = searchParams.get("mode");
  const initialMode: Mode =
    requestedMode === "research" || requestedMode === "explain" || requestedMode === "trade"
      ? requestedMode
      : "trade";

  return (
    <CopilotScreen
      key={`${initialMode}:${initialTicker}`}
      initialMode={initialMode}
      initialTicker={initialTicker}
    />
  );
}

function CopilotScreen({
  initialMode,
  initialTicker,
}: {
  initialMode: Mode;
  initialTicker: string;
}) {
  const { t } = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [ticker, setTicker] = useState(initialTicker);
  const [mode, setMode] = useState<Mode>(initialMode);

  const [events, setEvents] = useState<EventRecord[]>([]);
  const [output, setOutput] = useState<CopilotOutput | null>(null);
  const [loading, setLoading] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const endpointMap = {
    trade: "/trade/stream",
    research: "/research/stream",
    explain: "/explain/stream",
  };
  const fallbackEndpointMap = {
    trade: "/trade",
    research: "/research",
    explain: "/explain",
  };

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function run() {
    const clean = normalizeTicker(ticker);
    if (!clean) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setEvents([]);
    setOutput(null);
    setLoading(true);

    try {
      const completed = await runStream(clean, controller.signal);
      if (!completed && !controller.signal.aborted) {
        await runFallback(clean, controller.signal, "Streaming unavailable, switched to standard response.");
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        console.error(err);
        await runFallback(clean, controller.signal, "Streaming failed, switched to standard response.");
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  function stop() {
    abortRef.current?.abort();
    setLoading(false);
  }

  async function runStream(clean: string, signal: AbortSignal): Promise<boolean> {
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let sawFinalOutput = false;

    try {
      const res = await fetch(buildApiUrl(endpointMap[mode]), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: clean }),
        signal,
      });

      const contentType = res.headers.get("content-type") ?? "";
      reader = res.body?.getReader();

      if (!res.ok || !reader || !contentType.includes("text/event-stream")) {
        return false;
      }

      while (!signal.aborted) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";

        for (const chunk of chunks) {
          if (signal.aborted) {
            buffer = "";
            return sawFinalOutput;
          }

          const line = chunk.split("\n").find((entry) => entry.startsWith("data: "));
          if (!line) continue;

          let event: EventRecord;
          try {
            event = JSON.parse(line.replace("data: ", "")) as EventRecord;
          } catch (err) {
            if (signal.aborted) {
              buffer = "";
              return sawFinalOutput;
            }
            throw err;
          }

          pushEvent(event);

          if (event.type === "partial_output" || event.type === "final_output") {
            setOutput((prev) => mergeOutput(prev, event.data));
          }

          if (event.type === "final_output") {
            sawFinalOutput = true;
          }
        }
      }

      return sawFinalOutput;
    } catch (err) {
      if (signal.aborted) {
        buffer = "";
        return sawFinalOutput;
      }
      throw err;
    } finally {
      buffer = "";
      if (reader) {
        try {
          await reader.cancel();
        } catch {
          // The stream may already be closed or aborted.
        }
        try {
          reader.releaseLock();
        } catch {
          // The lock may already be released after cancellation.
        }
      }
    }
  }

  async function runFallback(clean: string, signal: AbortSignal, message: string) {
    pushEvent({
      type: "fallback",
      stage: "network",
      message,
    });

    const res = await fetch(buildApiUrl(fallbackEndpointMap[mode]), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: clean }),
      signal,
    });

    if (!res.ok) {
      let errorPayload: CopilotOutput | null = null;
      try {
        errorPayload = (await res.json()) as CopilotOutput;
      } catch {
        errorPayload = {
          ticker: clean,
          error: `Fallback request failed with status ${res.status}`,
        };
      }
      setOutput((prev) => mergeOutput(prev, errorPayload));
      pushEvent({
        type: "timeline_step",
        step: "final_answer",
        title: "Final Answer",
        status: "failed",
        summary: errorPayload.error ?? `Fallback request failed with status ${res.status}.`,
        timestamp: new Date().toISOString(),
        metadata: {
          source: "fallback",
          status: res.status,
          ticker: clean,
        },
      });
      throw new Error(errorPayload.error ?? `Fallback request failed with status ${res.status}`);
    }

    const raw = (await res.json()) as CopilotOutput;
    setOutput((prev) => mergeOutput(prev, raw));
    pushEvent({
      type: "timeline_step",
      step: "final_answer",
      title: "Final Answer",
      status: "completed",
      summary: "Loaded the final answer from the standard response path.",
      timestamp: new Date().toISOString(),
      metadata: {
        source: "fallback",
        ticker: clean,
      },
    });
    pushEvent({
      type: "final_output",
      stage: "fallback",
      message: "Final result loaded from the standard endpoint.",
      data: raw,
    });
  }

  function pushEvent(event: EventRecord) {
    setEvents((prev) => [...prev, event]);
  }

  function mergeOutput(current: CopilotOutput | null, incoming: unknown): CopilotOutput | null {
    if (!incoming || typeof incoming !== "object") {
      return current;
    }
    return {
      ...(current ?? {}),
      ...(incoming as CopilotOutput),
    };
  }

  function selectMode(nextMode: Mode) {
    setMode(nextMode);

    const params = new URLSearchParams(searchParams.toString());
    params.set("mode", nextMode);

    const clean = normalizeTicker(ticker);
    if (clean) {
      params.set("ticker", clean);
    } else {
      params.delete("ticker");
    }

    router.replace(`/copilot?${params.toString()}`);
  }

  const biasColor = useMemo(() => {
    if (!output?.bias) return "";
    if (output.bias === "Bullish") return "text-green-400";
    if (output.bias === "Bearish") return "text-red-400";
    return "text-yellow-300";
  }, [output]);

  const tickerMarket = useMemo(() => detectTickerMarket(ticker), [ticker]);
  const signal = useMemo(() => extractSignalViewModel(output), [output]);

  const latestMessage = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i -= 1) {
      if (events[i].summary) return events[i].summary;
      if (events[i].message) return events[i].message;
    }
    return "";
  }, [events]);

  const timelineItems = useMemo<TimelineItem[]>(() => {
    const order: TimelineStepKey[] = [
      "query_interpretation",
      "planning",
      "evidence_retrieval",
      "synthesis",
      "final_answer",
    ];
    const byStep = new Map<string, TimelineItem>();

    for (const event of events) {
      if (event.type !== "timeline_step" || !event.step || !event.title || !event.status || !event.summary) {
        continue;
      }

      byStep.set(event.step, {
        step: event.step,
        title: event.title,
        status: event.status,
        summary: event.summary,
        timestamp: event.timestamp,
        latency_ms: event.latency_ms,
        metadata: event.metadata,
      });
    }

    const ordered = order
      .filter((step) => byStep.has(step))
      .map((step) => byStep.get(step) as TimelineItem);

    const extras = [...byStep.values()].filter((item) => !order.includes(item.step as TimelineStepKey));
    return [...ordered, ...extras];
  }, [events]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white px-6 py-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <button
          onClick={() => router.push("/")}
          className="text-xl font-semibold hover:opacity-80"
        >
          {t.appName}
        </button>

        <div className="mt-3 flex gap-2">
          <button
            onClick={() => router.push("/portfolio")}
            className="rounded-xl border border-white/10 bg-zinc-900 px-4 py-2 text-sm"
          >
            {t.portfolio}
          </button>
        </div>

        <div className="mt-6 grid grid-cols-12 gap-6">
          {/* LEFT */}
          <div className="col-span-12 lg:col-span-4 bg-white/[0.03] p-4 rounded-2xl border border-white/10">
            <div className="text-sm text-zinc-400">Mode</div>

            <div className="flex gap-2 mt-3">
              {["trade", "research", "explain"].map((m) => (
                <button
                  key={m}
                  onClick={() => selectMode(m as Mode)}
                  className={`px-3 py-2 rounded-xl text-sm border ${
                    mode === m
                      ? "bg-white text-black"
                      : "bg-zinc-900 border-white/10"
                  }`}
                >
                  {m === "trade" ? "trade" : m === "research" ? t.research : t.explain}
                </button>
              ))}
            </div>

            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="NVDA, 2330, 2330.TW, 台積電..."
              className="mt-4 w-full px-4 py-3 rounded-xl bg-black border border-white/10"
            />

            {ticker ? (
              <div className="mt-2 text-xs text-zinc-400">
                {t.canonicalSymbol}: {normalizeTicker(ticker)}
                {tickerMarket ? ` • ${t.market}: ${tickerMarket}` : ""}
              </div>
            ) : null}

            <div className="flex gap-2 mt-4">
              <button
                onClick={run}
                className="flex-1 bg-white text-black py-3 rounded-xl"
              >
                {loading ? "Running..." : "Run"}
              </button>

              <button
                onClick={stop}
                className="px-4 py-3 rounded-xl border border-white/10"
              >
                Stop
              </button>
            </div>

            {/* OUTPUT */}
            {loading && latestMessage && (
              <div className="mt-6 rounded-xl border border-sky-400/20 bg-sky-400/10 p-3 text-sm text-sky-100">
                {latestMessage}
              </div>
            )}

            {output && mode === "trade" && (
              <div className="mt-6">
                <div className={`text-2xl font-bold ${biasColor}`}>
                  {output.bias}
                </div>
                <div className="text-sm text-zinc-400">
                  Confidence: {output.confidence}%
                </div>

                <div className="mt-3 text-sm space-y-1">
                  <div>Buy: {output.buy_zone}</div>
                  <div>Stop: {output.stop_loss}</div>
                  <div>Take: {output.take_profit}</div>
                </div>

                <div className="mt-3 text-xs text-zinc-500">
                  {output.reasoning?.map((r: string, i: number) => (
                    <div key={i}>• {r}</div>
                  ))}
                </div>

                {output.error && (
                  <div className="mt-3 text-sm text-rose-300">{output.error}</div>
                )}
                <EvidenceAudit output={output} />
              </div>
            )}

            {output && mode === "research" && (
              <div className="mt-6 text-sm space-y-2">
                <div>{output.fundamental_summary}</div>
                <div>{output.recent_news_summary}</div>
                <SignalPanel signal={signal} />
                <div className="text-green-400">{output.bull_case}</div>
                <div className="text-red-400">{output.bear_case}</div>
                {output.error && (
                  <div className="text-rose-300">{output.error}</div>
                )}
                <EvidenceAudit output={output} />
              </div>
            )}

            {output && mode === "explain" && (
              <div className="mt-6 text-sm space-y-2">
                <div>{output.price_move_summary}</div>
                <div>Confidence: {output.overall_confidence ?? 0}</div>
                <SignalPanel signal={signal} />
                {output.ranked_causes?.length ? (
                  <div className="space-y-2 pt-2">
                    {output.ranked_causes.slice(0, 3).map((cause, index) => (
                      <div
                        key={`${cause.cause ?? "cause"}-${index}`}
                        className="rounded-xl border border-white/10 bg-black/30 p-3"
                      >
                        <div className="font-medium">{cause.cause ?? "Candidate cause"}</div>
                        <div className="text-xs text-zinc-400">
                          Confidence: {cause.confidence ?? 0}
                        </div>
                        {cause.explanation && (
                          <div className="pt-1 text-zinc-300">{cause.explanation}</div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}
                {output.error && (
                  <div className="text-rose-300">{output.error}</div>
                )}
                <EvidenceAudit output={output} />
              </div>
            )}
          </div>

          {/* RIGHT (trace) */}
          <div className="col-span-12 lg:col-span-8 bg-white/[0.03] p-4 rounded-2xl border border-white/10">
            <div className="text-sm text-zinc-400">Execution Trace</div>

            <div className="mt-4 h-[600px] overflow-y-auto bg-black/40 p-4 rounded-xl text-sm font-mono">
              {timelineItems.length === 0 ? (
                <div className="text-sm text-zinc-500">
                  Run an analysis to see the reasoning timeline.
                </div>
              ) : (
                <div className="space-y-3 font-sans">
                  {timelineItems.map((item, index) => {
                    const statusTone =
                      item.status === "completed"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                        : item.status === "failed"
                          ? "border-rose-500/30 bg-rose-500/10 text-rose-100"
                          : "border-sky-500/30 bg-sky-500/10 text-sky-100";

                    return (
                      <details
                        key={`${item.step}-${index}`}
                        open={item.status === "in_progress"}
                        className={`rounded-xl border p-3 ${statusTone}`}
                      >
                        <summary className="cursor-pointer list-none">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-xs uppercase tracking-[0.18em] opacity-70">
                                Step {index + 1}
                              </div>
                              <div className="mt-1 font-semibold">{item.title}</div>
                              <div className="mt-1 text-sm opacity-90">{item.summary}</div>
                            </div>
                            <div className="text-right text-xs opacity-75">
                              <div>{item.status.replace("_", " ")}</div>
                              {item.latency_ms !== undefined ? <div>{item.latency_ms} ms</div> : null}
                            </div>
                          </div>
                        </summary>

                        <div className="mt-3 space-y-2 text-xs text-white/80">
                          {item.timestamp ? <div>Timestamp: {new Date(item.timestamp).toLocaleTimeString()}</div> : null}
                          {item.metadata && Object.keys(item.metadata).length > 0 ? (
                            <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                              {Object.entries(item.metadata).map(([key, value]) => (
                                <div key={key} className="flex gap-2 py-0.5">
                                  <span className="min-w-28 text-zinc-400">{key}</span>
                                  <span className="break-words">
                                    {Array.isArray(value) ? value.join(", ") : String(value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-zinc-400">No additional metadata.</div>
                          )}
                        </div>
                      </details>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
