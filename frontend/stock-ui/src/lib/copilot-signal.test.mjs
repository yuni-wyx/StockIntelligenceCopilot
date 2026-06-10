import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const projectRoot = process.cwd();
const moduleCache = new Map();
const require = createRequire(import.meta.url);

function resolveTsModule(specifier, parentPath) {
  if (specifier.startsWith("@/")) {
    const base = path.resolve(projectRoot, "src", specifier.slice(2));
    const candidates = [`${base}.ts`, `${base}.tsx`, base];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) return candidate;
    }
    return `${base}.ts`;
  }

  if (specifier.startsWith(".")) {
    const resolved = path.resolve(path.dirname(parentPath), specifier);
    const withTs = `${resolved}.ts`;
    const withTsx = `${resolved}.tsx`;
    if (fs.existsSync(withTs)) return withTs;
    if (fs.existsSync(withTsx)) return withTsx;
    if (fs.existsSync(resolved)) return resolved;
  }

  return specifier;
}

function loadTsModule(filePath) {
  const normalizedPath = path.resolve(filePath);
  if (moduleCache.has(normalizedPath)) {
    return moduleCache.get(normalizedPath).exports;
  }

  const source = fs.readFileSync(normalizedPath, "utf8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
      jsx: ts.JsxEmit.ReactJSX,
    },
    fileName: normalizedPath,
  }).outputText;

  const loadedModule = { exports: {} };
  moduleCache.set(normalizedPath, loadedModule);

  const localRequire = (specifier) => {
    const resolved = resolveTsModule(specifier, normalizedPath);
    if (resolved.endsWith(".ts") || resolved.endsWith(".tsx")) {
      return loadTsModule(resolved);
    }
    return require(resolved);
  };

  const wrapper = new Function(
    "require",
    "module",
    "exports",
    "__filename",
    "__dirname",
    transpiled,
  );
  wrapper(
    localRequire,
    loadedModule,
    loadedModule.exports,
    normalizedPath,
    path.dirname(normalizedPath),
  );
  return loadedModule.exports;
}

const { extractSignalViewModel } = loadTsModule(
  path.resolve(projectRoot, "src/components/copilot/signal.ts"),
);
const { SignalPanel } = loadTsModule(
  path.resolve(projectRoot, "src/components/copilot/SignalPanel.tsx"),
);
const { LanguageProvider } = loadTsModule(
  path.resolve(projectRoot, "src/context/LanguageContext.tsx"),
);

test("extractSignalViewModel returns structured signal when explicit signal payload exists", () => {
  const result = extractSignalViewModel({
    ticker: "NVDA",
    signal: {
      ticker: "NVDA",
      benchmark: "SPY",
      horizon_days: 30,
      signal_score: 67.2,
      signal_band: "Strong",
      confidence: "Medium",
      positive_signals: ["20d return beat SPY"],
      negative_signals: ["Volatility remains elevated"],
      data_caveats: ["Volume coverage incomplete"],
      disclaimer: "Structured disclaimer",
    },
  });

  assert.ok(result);
  assert.equal(result.usedFallbackParsing, false);
  assert.equal(result.signalScore, 67.2);
  assert.deepEqual(result.positiveSignals, ["20d return beat SPY"]);
  assert.deepEqual(result.negativeSignals, ["Volatility remains elevated"]);
  assert.deepEqual(result.dataCaveats, ["Volume coverage incomplete"]);
});

test("extractSignalViewModel parses fallback summary and caveats from research fields", () => {
  const result = extractSignalViewModel({
    ticker: "TSLA",
    fundamental_summary:
      "Relative signal: benchmark-relative strength versus SPY over 30 days is Strong (score 61.0, confidence Low).",
    recent_news_summary:
      "Headline wrap. Signal caveats: Short history reduces confidence. Mixed signals remain across momentum and volatility.",
  });

  assert.ok(result);
  assert.equal(result.usedFallbackParsing, true);
  assert.equal(result.benchmark, "SPY");
  assert.equal(result.horizonDays, 30);
  assert.equal(result.signalBand, "Strong");
  assert.equal(result.signalScore, 61);
  assert.equal(result.confidence, "Low");
  assert.deepEqual(result.dataCaveats, [
    "Short history reduces confidence.",
    "Mixed signals remain across momentum and volatility.",
  ]);
});

test("extractSignalViewModel returns null when signal evidence is unavailable", () => {
  const result = extractSignalViewModel({
    ticker: "AAPL",
    fundamental_summary: "Revenue remained resilient.",
    recent_news_summary: "No signal marker included here.",
  });

  assert.equal(result, null);
});

test("extractSignalViewModel parses caveats from explain volume context", () => {
  const result = extractSignalViewModel({
    ticker: "2330.TW",
    price_move_summary:
      "Relative signal: benchmark-relative strength versus SPY over 30 days is Neutral (score 52.5, confidence Low).",
    volume_context:
      "Signal caveats: Missing volume confirmation. Benchmark history was shorter than ideal.",
  });

  assert.ok(result);
  assert.equal(result.confidence, "Low");
  assert.deepEqual(result.dataCaveats, [
    "Missing volume confirmation.",
    "Benchmark history was shorter than ideal.",
  ]);
});

test("SignalPanel renders low-confidence warning and caveats", () => {
  const markup = renderToStaticMarkup(
    React.createElement(
      LanguageProvider,
      null,
      React.createElement(SignalPanel, {
        signal: {
          ticker: "TSLA",
          benchmark: "SPY",
          horizonDays: 30,
          signalScore: 44.2,
          signalBand: "Neutral",
          confidence: "Low",
          positiveSignals: [],
          negativeSignals: [],
          dataCaveats: ["Short history reduces confidence."],
          disclaimer: "Heuristic estimate only.",
          usedFallbackParsing: true,
        },
      }),
    ),
  );

  assert.match(markup, /Relative Signal/);
  assert.match(markup, /Low confidence: review caveats before relying on this signal\./);
  assert.match(markup, /Short history reduces confidence\./);
});

test("SignalPanel hides cleanly when signal is missing", () => {
  const markup = renderToStaticMarkup(
    React.createElement(
      LanguageProvider,
      null,
      React.createElement(SignalPanel, { signal: null }),
    ),
  );

  assert.equal(markup, "");
});
