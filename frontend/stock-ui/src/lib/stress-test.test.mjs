import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import ts from "typescript";

const projectRoot = process.cwd();
const moduleCache = new Map();
const require = createRequire(import.meta.url);

function resolveTsModule(specifier, parentPath) {
  if (specifier.startsWith("@/")) {
    return path.resolve(projectRoot, "src", `${specifier.slice(2)}.ts`);
  }

  if (specifier.startsWith(".")) {
    const resolved = path.resolve(path.dirname(parentPath), specifier);
    const withTs = `${resolved}.ts`;
    if (fs.existsSync(withTs)) return withTs;
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
    },
    fileName: normalizedPath,
  }).outputText;

  const loadedModule = { exports: {} };
  moduleCache.set(normalizedPath, loadedModule);

  const localRequire = (specifier) => {
    const resolved = resolveTsModule(specifier, normalizedPath);
    if (resolved.endsWith(".ts")) {
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

const { runPortfolioStressTest } = loadTsModule(
  path.resolve(projectRoot, "src/components/wealth-studio/stressTest.ts"),
);

const messages = {
  stressTestNoValidHoldings: "NO_VALID_HOLDINGS",
  stressTestCustomTickerRequired: "CUSTOM_TICKER_REQUIRED",
  stressTestShockRequired: "SHOCK_REQUIRED",
  stressTestShockRange: "SHOCK_RANGE",
  stressTestBroadMarketExplanation: "BROAD_MARKET",
  stressTestTechnologyExplanation: "TECH_SELL_OFF",
  stressTestTaiwanExplanation: "TAIWAN_SELL_OFF",
  stressTestBondExplanation: "BOND_SELL_OFF",
  stressTestCustomExplanation: "CUSTOM_{ticker}",
  stressTestNoMatchingHoldings: "NO_MATCHING_HOLDINGS",
};

function holding({
  ticker,
  name = "",
  shares = "0",
  currentPrice,
  currentValue,
  assetType = "",
  category = "",
  notes = "",
}) {
  return {
    _rowId: `row-${ticker}`,
    ticker,
    name,
    shares,
    current_price: currentPrice,
    current_value: currentValue,
    avg_cost: "0",
    asset_type: assetType,
    category,
    notes,
  };
}

test("broad market -20% affects all valid holdings", () => {
  const holdings = [
    holding({ ticker: "NVDA", shares: "10", currentPrice: "100" }),
    holding({ ticker: "2330", shares: "5", currentPrice: "200" }),
  ];

  const { error, result } = runPortfolioStressTest(holdings, {
    preset: "broad_market_20",
    customTicker: "",
    customShockPct: "-20",
  }, messages);

  assert.equal(error, null);
  assert.ok(result);
  assert.equal(result.beforeValue, 2000);
  assert.equal(result.afterValue, 1600);
  assert.equal(result.delta, -400);
  assert.equal(result.deltaPct, -20);
  assert.equal(result.impactedHoldings.length, 2);
});

test("custom ticker shock affects only the matching ticker", () => {
  const holdings = [
    holding({ ticker: "NVDA", shares: "10", currentPrice: "100", category: "Technology" }),
    holding({ ticker: "00878", shares: "100", currentPrice: "20", category: "High Dividend" }),
  ];

  const { error, result } = runPortfolioStressTest(holdings, {
    preset: "custom_ticker",
    customTicker: "nvda",
    customShockPct: "-20",
  }, messages);

  assert.equal(error, null);
  assert.ok(result);
  assert.equal(result.beforeValue, 3000);
  assert.equal(result.afterValue, 2800);
  assert.equal(result.impactedHoldings.length, 1);
  assert.equal(result.impactedHoldings[0].ticker, "NVDA");
  assert.equal(result.impactedHoldings[0].afterValue, 800);
});

test("unknown custom ticker leaves holdings unchanged and returns friendly explanation", () => {
  const holdings = [
    holding({ ticker: "NVDA", shares: "10", currentPrice: "100" }),
  ];

  const { error, result } = runPortfolioStressTest(holdings, {
    preset: "custom_ticker",
    customTicker: "AAPL",
    customShockPct: "-20",
  }, messages);

  assert.equal(error, null);
  assert.ok(result);
  assert.equal(result.beforeValue, 1000);
  assert.equal(result.afterValue, 1000);
  assert.equal(result.delta, 0);
  assert.equal(result.impactedHoldings.length, 0);
  assert.equal(result.explanation, "NO_MATCHING_HOLDINGS");
});

test("technology selloff affects only technology or AI themed holdings", () => {
  const holdings = [
    holding({ ticker: "NVDA", shares: "10", currentPrice: "100", category: "Technology / AI" }),
    holding({ ticker: "BND", shares: "10", currentPrice: "50", assetType: "Bond ETF" }),
    holding({ ticker: "00878", shares: "100", currentPrice: "20", category: "High Dividend" }),
  ];

  const { error, result } = runPortfolioStressTest(holdings, {
    preset: "technology_selloff_15",
    customTicker: "",
    customShockPct: "-20",
  }, messages);

  assert.equal(error, null);
  assert.ok(result);
  assert.equal(result.beforeValue, 3500);
  assert.equal(result.afterValue, 3350);
  assert.equal(result.delta, -150);
  assert.equal(result.impactedHoldings.length, 1);
  assert.equal(result.impactedHoldings[0].ticker, "NVDA");
  assert.equal(result.impactedHoldings[0].deltaPct, -15);
});

test("no valid holdings returns a validation error", () => {
  const holdings = [
    holding({ ticker: "", shares: "0", currentPrice: "" }),
    holding({ ticker: "NVDA", shares: "0", currentPrice: "100" }),
  ];

  const { error, result } = runPortfolioStressTest(holdings, {
    preset: "broad_market_20",
    customTicker: "",
    customShockPct: "-20",
  }, messages);

  assert.equal(error, "NO_VALID_HOLDINGS");
  assert.equal(result, null);
});

test("shock percentage bounds reject values outside -100 to 100", () => {
  const holdings = [
    holding({ ticker: "NVDA", shares: "10", currentPrice: "100" }),
  ];

  const tooLow = runPortfolioStressTest(holdings, {
    preset: "custom_ticker",
    customTicker: "NVDA",
    customShockPct: "-101",
  }, messages);
  const tooHigh = runPortfolioStressTest(holdings, {
    preset: "custom_ticker",
    customTicker: "NVDA",
    customShockPct: "101",
  }, messages);

  assert.equal(tooLow.error, "SHOCK_RANGE");
  assert.equal(tooLow.result, null);
  assert.equal(tooHigh.error, "SHOCK_RANGE");
  assert.equal(tooHigh.result, null);
});
