# AGENTS.md

## Repo Purpose

This repository powers **Stock Intelligence Copilot**, a full-stack AI investment research and portfolio intelligence platform with:

- ticker-level research for US and Taiwan stocks, ETFs, and funds
- explain mode for price-move analysis
- trade mode for structured setup analysis
- watchlist monitoring
- Wealth Studio portfolio workspace
- portfolio analysis, scenario comparison, and stress testing
- Signal Engine and relative signal summaries
- evidence aggregation and provenance tracking
- SSE streaming with cancellation cleanup
- safe runtime fallback and HTTP error semantics

This project is for analysis, education, and demo use. It must not imply financial advice, price prediction, or guaranteed returns.

## Architecture Summary

- Backend: FastAPI in [backend/main.py](/Users/yuni/stock_intelligence_copilot/backend/main.py)
- Frontend: Next.js app in [frontend/stock-ui](/Users/yuni/stock_intelligence_copilot/frontend/stock-ui)
- Unified agent runtime:
  - shared task/result contracts in [backend/schemas/agent.py](/Users/yuni/stock_intelligence_copilot/backend/schemas/agent.py)
  - shared runtime entrypoint in [backend/pipeline/agent_runtime.py](/Users/yuni/stock_intelligence_copilot/backend/pipeline/agent_runtime.py)
- Deterministic analysis layers:
  - planning, retrieval, synthesis, route adapters, and orchestration under [backend/pipeline](/Users/yuni/stock_intelligence_copilot/backend/pipeline)
  - ticker tools under [backend/tools](/Users/yuni/stock_intelligence_copilot/backend/tools)
  - portfolio calculator under [backend/services/portfolio_calculator.py](/Users/yuni/stock_intelligence_copilot/backend/services/portfolio_calculator.py)
  - portfolio persistence under [backend/services/portfolio_store.py](/Users/yuni/stock_intelligence_copilot/backend/services/portfolio_store.py)
  - evidence services under [backend/services](/Users/yuni/stock_intelligence_copilot/backend/services)
- Portfolio-specific adapters and synthesis remain under:
  - [backend/pipeline/portfolio_orchestrator.py](/Users/yuni/stock_intelligence_copilot/backend/pipeline/portfolio_orchestrator.py)
  - [backend/pipeline/portfolio_agent.py](/Users/yuni/stock_intelligence_copilot/backend/pipeline/portfolio_agent.py)

### Unified Runtime Diagram

```text
Agent Task
  ↓
Planner
  ↓
Tool Router / Service Wrappers
  ↓
Evidence Bundle
  ↓
Synthesis
  ↓
Agent Result
```

## Current Runtime Migration Status

- Non-streaming ticker routes enter through the unified runtime with safe fallback:
  - research
  - explain
  - trade
  - watchlist
- Portfolio routes execute through runtime-backed adapters.
- Streaming routes use a runtime-aware SSE adapter for:
  - research
  - explain
  - trade
- `watchlist` has no public stream route yet.
- The streaming adapter may emit compatibility milestones before deeper runtime-native streaming is complete.

## Agent Operating Rules

- Read the relevant files before editing.
- Keep changes small, scoped, and reviewable.
- Do not refactor unrelated code during feature or bug-fix work.
- Respect a dirty working tree. Do not revert or overwrite changes you did not make.
- Prefer existing architecture, schemas, adapters, and helper functions over new parallel paths.
- Prefer deterministic calculations and source-backed evidence before adding ML, LLM, embeddings, or new providers.
- Explain before large changes. Ask Yuni before risky or product-direction changes.
- Prioritize demo-readiness, resume value, and maintainability over overengineering.

## Safe Local Testing Rules

- Do not open `localhost` automatically.
- Do not use browser automation unless Yuni explicitly requests it.
- Do not run Playwright unless Yuni explicitly requests it.
- Do not start long-running dev servers unless the task explicitly requires it.
- Use curl-first checks before any manual browser testing:

```bash
curl -I http://localhost:3000
curl -I http://localhost:3000/copilot
curl -I http://localhost:3000/portfolio
curl -I http://localhost:8000/health
```

If a dev server is already running, prefer lightweight `curl` checks over opening a browser.

## Local Dev Memory Warning

Opening `localhost:3000` previously caused severe local memory spikes and Mac freezes. Treat this as a known local development hazard, not proof of a React app runtime leak.

Likely contributors:

- Next 16 development toolchain behavior
- Turbopack
- `reactCompiler: true`
- `nxnode.bin` / `next-server` memory growth

The safer local setup is:

- `reactCompiler: false`
- `next dev --webpack`
- curl-first verification before opening a browser

Do not re-enable Turbopack or React Compiler for debugging unless Yuni explicitly asks to test those tools.

## Manual Approval Rules

Ask Yuni before introducing or enabling any of the following:

- paid APIs
- new LLM APIs
- model training
- embeddings
- vector databases
- cloud resources
- new API keys or secrets
- new external data providers with usage limits or billing risk

Existing optional provider integrations must remain clearly documented and guarded by environment variables.

## Commands

- Backend run: `./.venv/bin/python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend run: `cd frontend/stock-ui && npm run dev`
- Backend tests: `./.venv/bin/python -m unittest discover -s tests -v`
- Backend lint: `./.venv/bin/python -m ruff check backend tests`
- Frontend lint: `cd frontend/stock-ui && npm run lint`

Run only the smallest relevant test set for the current change unless broader verification is requested.

## Commit Hygiene

- Check `git status --short` before planning commits.
- Group commits by coherent product or architecture change.
- Do not mix documentation-only changes with application logic changes.
- Do not stage unrelated dirty files.
- Mention tests or checks run in the final report.
- If no tests were run because the change is documentation-only, say so.

## Coding Rules

- Preserve existing research/explain/trade/watchlist routes and behavior unless a change is explicitly required.
- Keep frontend API composition centralized in `buildApiUrl()`.
- Keep schemas explicit and typed.
- Use existing tool modules before inventing new data paths.
- Prefer routing new backend capabilities through the unified agent runtime instead of creating a separate orchestration path.
- Keep response shapes backward compatible unless a contract change is explicitly required.

## Error Handling Rules

- Runtime or fallback failures must not return HTTP 200 with an error payload.
- Validation and user-input errors should return 400 or 422.
- Runtime, tool, or provider failures should return 500 or 502.
- Preserve frontend-compatible error fields where possible.
- Do not expose secrets, internal tracebacks, or provider credentials to users.
- Do not swallow errors as successful events.

## Streaming / SSE Safety Rules

- Streaming routes must handle client disconnects and cancellation safely.
- If FastAPI `Request` is available, stream generators should check `await request.is_disconnected()` between streaming steps.
- Catch and clean up `GeneratorExit`, `asyncio.CancelledError`, and disconnect-related cancellation paths.
- Frontend stream readers should abort, cancel readers, release locks, clear controller refs, and stop loading states.
- Do not emit final success events after cancellation.
- Avoid orphaned stream readers, generators, or long-running agent tasks.

## Financial Safety Rules

- Do not hallucinate financial data.
- Any number must come from:
  - user input
  - deterministic calculations
  - fetched tool output
  - explicit source metadata
- If data is missing, say it is missing.
- Frame output as analysis, review items, and tradeoffs, not guarantees or promises.
- Use cautious language such as:
  - heuristic estimate
  - relative signal
  - stress test
  - suggested review item
  - not financial advice

Avoid wording that implies:

- guaranteed returns
- price prediction certainty
- personalized regulated investment advice
- objective investment ratings when the value is heuristic

## Portfolio Mode Principles

- Portfolio mode is personalized analysis of user-provided holdings, not generic ticker research.
- Concentration, dividend tradeoffs, missing data, downside risk, and data quality must be surfaced clearly.
- Reallocation output should compare before vs after and explain what changed.
- Defensive allocation should not be dismissed casually.
- Health, diversification, income, defensive, growth, and concentration outputs are heuristic and must be described as estimates.
- Exposure tagging is heuristic and must be presented as approximate where appropriate.
- Deterministic metrics such as cost basis, current value, unrealized gain/loss, and return percentage should remain clearly separated from heuristic estimates.
