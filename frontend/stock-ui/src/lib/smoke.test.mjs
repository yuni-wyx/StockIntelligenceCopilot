import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const read = (relativePath) =>
  fs.readFileSync(path.resolve(process.cwd(), relativePath), "utf8");

test("portfolio page source exists with holdings UI and add-row entrypoint", () => {
  const source = read("src/app/portfolio/page.tsx");
  const messages = read("src/i18n/messages.tsx");
  assert.match(source, /Holdings/);
  assert.match(source, /analyzeHoldings/);
  assert.match(source, /addHolding/);
  assert.match(source, /saveWorkspace/);
  assert.match(source, /loadSaved/);
  assert.match(source, /overallHealth/);
  assert.match(source, /aiPortfolioCoach/);
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
