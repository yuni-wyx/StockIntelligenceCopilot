import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const read = (relativePath) =>
  fs.readFileSync(path.resolve(process.cwd(), relativePath), "utf8");

test("portfolio page coordinates wealth studio sections and extracted components", () => {
  const source = read("src/app/portfolio/page.tsx");
  const holdingsEditor = read("src/components/wealth-studio/PortfolioHoldingsEditor.tsx");
  const snapshotPanel = read("src/components/wealth-studio/PortfolioSnapshotPanel.tsx");
  const snapshotSections = read("src/components/wealth-studio/PortfolioSnapshotSections.tsx");
  const coachPanel = read("src/components/wealth-studio/PortfolioCoachPanel.tsx");
  const monitorPanel = read("src/components/wealth-studio/PortfolioMonitorPanel.tsx");
  const stressTestPanel = read("src/components/wealth-studio/PortfolioStressTestSection.tsx");
  const messages = read("src/i18n/messages.tsx");
  assert.match(source, /PortfolioHoldingsEditor/);
  assert.match(source, /PortfolioSnapshotPanel/);
  assert.match(source, /PortfolioCoachPanel/);
  assert.match(source, /PortfolioMonitorPanel/);
  assert.match(source, /SavedWorkspacesPanel/);
  assert.match(source, /PortfolioScenarioPanel/);
  assert.match(source, /runPortfolioStressTest/);
  assert.match(source, /previewPortfolioImport/);
  assert.match(holdingsEditor, /addHolding/);
  assert.match(holdingsEditor, /csvImportTitle/);
  assert.match(holdingsEditor, /csvApplyImport/);
  assert.match(holdingsEditor, /importOnboardingTitle/);
  assert.match(holdingsEditor, /importNextActions/);
  assert.match(holdingsEditor, /saveWorkspace/);
  assert.match(holdingsEditor, /loadSaved/);
  assert.match(snapshotPanel, /SnapshotOverview/);
  assert.match(snapshotSections, /overallHealth/);
  assert.match(coachPanel, /askAboutMyPortfolio/);
  assert.match(monitorPanel, /portfolioMonitorTopAlerts/);
  assert.match(monitorPanel, /portfolioMonitorSourceSignal/);
  assert.match(stressTestPanel, /runStressTest/);
  assert.match(source, /addHolding/);
  assert.match(messages, /Portfolio Snapshot/);
  assert.match(messages, /Portfolio Stress Test/);
  assert.match(messages, /Ask About My Portfolio/);
  assert.match(messages, /Portfolio Monitor/);
  assert.match(messages, /Import Summary and Next Review/);
});

test("api base source builds urls under /api and requires deployed env config", () => {
  const source = read("src/lib/apiBase.ts");
  const portfolioApi = read("src/lib/portfolioApi.ts");
  assert.match(source, /NEXT_PUBLIC_BACKEND_BASE_URL/);
  assert.match(source, /http:\/\/localhost:8000/);
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
