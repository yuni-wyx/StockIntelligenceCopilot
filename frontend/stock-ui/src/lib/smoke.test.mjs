import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const read = (relativePath) =>
  fs.readFileSync(path.resolve(process.cwd(), relativePath), "utf8");

test("portfolio page renders chat-first portfolio MVP coordinator", () => {
  const source = read("src/app/portfolio/page.tsx");
  const chatMvp = read("src/components/wealth-studio/PortfolioChatMvp.tsx");
  const parser = read("src/components/wealth-studio/portfolioChatParser.ts");
  const messages = read("src/i18n/messages.tsx");
  assert.match(source, /PortfolioChatMvp/);
  assert.match(source, /PortfolioChatLoadingShell/);
  assert.match(source, /loadCurrentPortfolio/);
  assert.match(source, /savePortfolio/);
  assert.match(source, /askAboutPortfolio/);
  assert.match(source, /parsePortfolioHoldingsText/);
  assert.doesNotMatch(source, /PortfolioHoldingsEditor/);
  assert.doesNotMatch(source, /PortfolioSnapshotPanel/);
  assert.doesNotMatch(source, /PortfolioScenarioPanel/);
  assert.doesNotMatch(source, /PortfolioMonitorPanel/);
  assert.doesNotMatch(source, /holding-initial-00878/);
  assert.match(chatMvp, /CONFIRM_HOLDINGS/);
  assert.match(chatMvp, /LanguageToggle/);
  assert.match(chatMvp, /\/copilot\?mode=research/);
  assert.match(source, /PORTFOLIO_SAVED/);
  assert.match(chatMvp, /Portfolio memory is ready|portfolioMemoryReady/);
  assert.match(parser, /兆利/);
  assert.match(parser, /中華/);
  assert.match(parser, /我有\|我持有\|目前有\|另外有/);
  assert.match(parser, /平均買在/);
  assert.match(parser, /00878\.TW/);
  assert.match(messages, /Portfolio Copilot/);
  assert.match(messages, /投資組合助手/);
  assert.match(messages, /This is an educational portfolio review/);
  assert.match(messages, /這是教育用途的投資組合檢視/);
});

test("language provider defers persisted locale until after hydration", () => {
  const context = read("src/context/LanguageContext.tsx");
  const toggle = read("src/components/LanguageToggle.tsx");
  const portfolioPage = read("src/app/portfolio/page.tsx");

  assert.match(context, /useState<Locale>\("en"\)/);
  assert.match(context, /useEffect/);
  assert.match(context, /localStorage\.getItem\(STORAGE_KEY\)/);
  assert.match(context, /hydrated/);
  assert.match(portfolioPage, /if \(!hydrated\)/);
  assert.match(toggle, /English/);
  assert.match(toggle, /繁體中文/);
});

test("api base source builds urls under /api and requires deployed env config", () => {
  const source = read("src/lib/apiBase.ts");
  const portfolioApi = read("src/lib/portfolioApi.ts");
  assert.match(source, /NEXT_PUBLIC_BACKEND_BASE_URL/);
  assert.match(source, /http:\/\/\$\{host\}:8000/);
  assert.match(source, /\/api\$\{path\}/);
  assert.match(portfolioApi, /\/portfolio\/chat/);
  assert.match(portfolioApi, /\/portfolio\/monitor/);
  assert.match(portfolioApi, /\/portfolio\/import\/preview/);
});

test("research mode still exists in copilot source", () => {
  const source = read("src/app/copilot/page.tsx");
  assert.match(source, /research/);
  assert.match(source, /SignalPanel/);
  assert.match(source, /extractSignalViewModel/);
  assert.match(source, /Primary filings/);
  assert.match(source, /Tier 1 filing sources linked/);
  assert.match(source, /source_type === "filing"/);
  assert.match(source, /research_conflicts/);
  assert.match(source, /Research data quality notes/);
  assert.match(source, /research_conflict_details/);
  assert.match(source, /data_as_of/);
});

test("signal panel labels are defined for english and traditional chinese", () => {
  const messages = read("src/i18n/messages.tsx");
  const signalPanel = read("src/components/copilot/SignalPanel.tsx");
  assert.match(messages, /Relative Signal/);
  assert.match(messages, /相對訊號/);
  assert.match(signalPanel, /signalLowConfidenceNote/);
  assert.match(signalPanel, /benchmarkRelativeStrength/);
});

test("home page links to portfolio mode", () => {
  const source = read("src/app/page.tsx");
  assert.match(source, /Portfolio Mode/);
  assert.match(source, /\/portfolio/);
});
