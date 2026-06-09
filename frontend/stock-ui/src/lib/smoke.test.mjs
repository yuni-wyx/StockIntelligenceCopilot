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
  const coachPanel = read("src/components/wealth-studio/PortfolioCoachPanel.tsx");
  const messages = read("src/i18n/messages.tsx");
  assert.match(source, /PortfolioHoldingsEditor/);
  assert.match(source, /PortfolioSnapshotPanel/);
  assert.match(source, /PortfolioCoachPanel/);
  assert.match(source, /SavedWorkspacesPanel/);
  assert.match(source, /PortfolioScenarioPanel/);
  assert.match(holdingsEditor, /addHolding/);
  assert.match(holdingsEditor, /saveWorkspace/);
  assert.match(holdingsEditor, /loadSaved/);
  assert.match(snapshotPanel, /overallHealth/);
  assert.match(coachPanel, /aiPortfolioCoach/);
  assert.match(source, /addHolding/);
  assert.match(messages, /Portfolio Snapshot/);
  assert.match(messages, /AI Portfolio Coach/);
});

test("api base source builds urls under /api and requires deployed env config", () => {
  const source = read("src/lib/apiBase.ts");
  assert.match(source, /NEXT_PUBLIC_BACKEND_BASE_URL/);
  assert.match(source, /http:\/\/localhost:8000/);
  assert.match(source, /\/api\$\{path\}/);
});

test("research mode still exists in copilot source", () => {
  const source = read("src/app/copilot/page.tsx");
  assert.match(source, /research/);
});

test("home page links to portfolio mode", () => {
  const source = read("src/app/page.tsx");
  assert.match(source, /Portfolio Mode/);
  assert.match(source, /\/portfolio/);
});
