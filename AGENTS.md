# AGENTS.md

## Repo Purpose

This repository powers **Stock Intelligence Copilot**, a full-stack financial analysis product with:

- ticker-level research for US and Taiwan stocks, ETFs, and funds
- explain mode for price-move analysis
- trade mode for structured setup analysis
- watchlist monitoring
- portfolio mode for personal holdings analysis and reallocation scenarios
- persistent portfolio save/load support for local demo use
- portfolio agent recommendations backed by deterministic calculations and tool evidence

## Architecture Summary

- Backend: FastAPI in [backend/main.py](/Users/yuni/stock_intelligence_copilot/backend/main.py)
- Frontend: Next.js app in [frontend/stock-ui](/Users/yuni/stock_intelligence_copilot/frontend/stock-ui)
- Unified agent runtime:
  - shared task/result contracts in [backend/schemas/agent.py](/Users/yuni/stock_intelligence_copilot/backend/schemas/agent.py)
  - shared runtime entrypoint in [backend/pipeline/agent_runtime.py](/Users/yuni/stock_intelligence_copilot/backend/pipeline/agent_runtime.py)
- Deterministic analysis layers:
  - query planning/retrieval/synthesis under [backend/pipeline](/Users/yuni/stock_intelligence_copilot/backend/pipeline)
  - ticker tools under [backend/tools](/Users/yuni/stock_intelligence_copilot/backend/tools)
- portfolio calculator under [backend/services/portfolio_calculator.py](/Users/yuni/stock_intelligence_copilot/backend/services/portfolio_calculator.py)
- portfolio persistence under [backend/services/portfolio_store.py](/Users/yuni/stock_intelligence_copilot/backend/services/portfolio_store.py)
- portfolio-specific adapters and synthesis remain under:
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

## Unified Runtime Migration Status

- Non-streaming ticker routes now enter through the unified runtime with legacy fallback:
  - research
  - explain
  - trade
  - watchlist
- Portfolio routes already execute through runtime-backed adapters.
- Streaming routes now use a runtime streaming adapter for:
  - research
  - explain
  - trade
- `watchlist` still has no public stream route.
- The streaming adapter currently emits compatibility milestones first; deeper runtime-native streaming can come later.

## Commands

- Backend run: `./.venv/bin/python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend run: `cd frontend/stock-ui && npm run dev`
- Backend tests: `./.venv/bin/python -m unittest discover -s tests -v`
- Backend lint: `./.venv/bin/python -m ruff check backend tests`
- Frontend lint: `cd frontend/stock-ui && npm run lint`

## Coding Rules

- Preserve existing research/explain/trade/watchlist routes and behavior unless a change is explicitly required.
- Prefer deterministic calculations for anything numeric.
- Keep schemas explicit and typed.
- Use existing tool modules before inventing new data paths.
- Keep frontend API composition centralized in `buildApiUrl()`.
- Prefer routing new backend capabilities through the unified agent runtime instead of creating a separate orchestration path.

## Financial Safety Rules

- Do not hallucinate financial data.
- Any number must come from:
  - user input
  - deterministic calculations
  - fetched tool output
- If data is missing, say it is missing.
- Frame output as analysis and tradeoffs, not guarantees or promises.

## Portfolio Mode Principles

- Portfolio mode is personalized analysis, not generic ticker research.
- Concentration, dividend tradeoffs, missing data, and downside risk must be surfaced clearly.
- Reallocation output should compare before vs after and explain what changed.
- Defensive allocation should not be dismissed casually.
- Health scores are heuristic and should be described as heuristics, not objective truth.
- Exposure tagging is heuristic and must be presented as approximate where appropriate.
