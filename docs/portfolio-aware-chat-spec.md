# Week 4.5: Portfolio Memory + Portfolio-Aware Chat

## Goal

Turn Wealth Studio from a portfolio analytics dashboard into a **portfolio-aware investment copilot** that remembers the saved or current workspace and uses that context in natural portfolio questions.

This milestone is documentation and implementation planning only. It does not introduce new application code, dependencies, cloud services, model training, embeddings, vector databases, brokerage integrations, or paid APIs.

## Why This Matters

Current friction:

- users save a portfolio in Wealth Studio
- then still need to restate holdings or context when asking follow-up questions
- natural questions such as `00878 要不要減碼？` or `中華還值得抱嗎？` do not yet benefit from portfolio memory by default

Desired outcome:

- save holdings once
- ask questions later without re-entering context
- answer using holdings, weights, portfolio intelligence, stress tests, signal evidence, and relevant market evidence

## User Stories

- As a user, I can save my holdings once and ask portfolio questions later without retyping them.
- As a user, I can ask `兆利跟中華怎麼配置？` and the system uses my saved holdings and current weights.
- As a user, I can ask whether my portfolio is too concentrated and get a review-oriented answer grounded in deterministic portfolio intelligence.
- As a user, I can ask about dividend quality, stress-test sensitivity, and earnings-related risk using the same saved workspace.
- As a user, I receive cautious analysis rather than direct commands, predictions, or guaranteed-return language.

## Product Principles

- Portfolio memory starts from the saved or current Wealth Studio workspace.
- Context assembly should be deterministic first.
- Evidence should be layered, not invented.
- The copilot should support natural conversation, but remain privacy-conscious and non-advisory.
- Numbers must come from:
  - saved holdings
  - deterministic portfolio calculations
  - explicit stress-test results
  - signal engine output
  - fetched market, news, fundamentals, or earnings evidence

## Proposed Architecture

```text
Saved / Current Workspace
  ↓
PortfolioContextBuilder
  ↓
Portfolio Context Bundle
  ├─ holdings snapshot
  ├─ deterministic metrics
  ├─ portfolio intelligence
  ├─ stress-test summary
  ├─ signal evidence
  └─ market / news / earnings evidence
  ↓
Portfolio-Aware Chat Orchestrator
  ↓
Grounded portfolio-aware response
```

### Proposed Components

- `PortfolioContextBuilder`
  - builds a compact, privacy-conscious portfolio context object from saved/current workspace data
- `PortfolioAwareChatRequest`
  - user question plus optional overrides
- `PortfolioAwareChatResponse`
  - structured answer with conclusion, evidence, review items, risks, and missing data
- saved workspace context loader
  - uses existing local persistence before any new memory system
- evidence injectors
  - portfolio intelligence
  - stress test summary
  - signal evidence
  - market / news / earnings evidence when relevant

## Backend Plan

Potential files:

- `backend/services/portfolio_context_builder.py`
- `backend/schemas/portfolio_chat.py`
- `backend/pipeline/portfolio_chat_orchestrator.py`
- or a clean extension inside `backend/pipeline/portfolio_agent.py`
- `tests/test_portfolio_context_builder.py`
- `tests/test_portfolio_chat.py`

### Backend Responsibilities

1. Load saved or current workspace.
2. Normalize holdings and deterministic metrics.
3. Attach available portfolio intelligence.
4. Attach latest relevant stress-test summary if present.
5. Attach benchmark-relative signal evidence for referenced holdings when available.
6. Attach market/news/earnings evidence for question-relevant tickers.
7. Produce a structured, evidence-based portfolio-aware answer.

### Suggested Request / Response Direction

Potential request shape:

```json
{
  "question": "兆利跟中華目前可以怎麼配置？",
  "use_saved_workspace": true,
  "target_tickers": ["3548.TW", "2204.TW"]
}
```

Potential response direction:

```json
{
  "conclusion": "目前兩檔都值得列入重點檢查名單，但應先從持股權重、未實現損益與集中度風險一起看。",
  "portfolio_context_used": true,
  "key_numbers": [],
  "evidence_used": [],
  "suggested_review_items": [],
  "risks": [],
  "missing_data": [],
  "disclaimer": "This response is for analysis only and is not financial advice."
}
```

## Frontend Plan

Potential files:

- `frontend/stock-ui/src/components/wealth-studio/PortfolioChatPanel.tsx`
- `frontend/stock-ui/src/components/wealth-studio/PortfolioQuestionChips.tsx`
- `frontend/stock-ui/src/i18n/messages.tsx`
- `frontend/stock-ui/src/lib/portfolioApi.ts`

### Frontend MVP

- Add an **Ask About My Portfolio** panel inside Wealth Studio.
- Use saved/current workspace as the default memory source.
- Provide starter question chips:
  - `我的風險高嗎？`
  - `我是不是太集中？`
  - `兆利跟中華怎麼配置？`
  - `配息收入穩定嗎？`
  - `如果科技股下跌，我受影響大嗎？`
- Show whether the answer used:
  - saved holdings
  - portfolio intelligence
  - stress-test context
  - signal evidence
  - market/news/earnings evidence

## MVP Behavior

- User saves or loads a workspace once.
- User opens Wealth Studio and asks a natural portfolio question.
- System automatically uses the current or saved workspace as context.
- System adds:
  - holdings
  - weights
  - cost basis / current value when available
  - portfolio intelligence
  - stress test summary if available
  - signal evidence if relevant
- Response stays grounded, cautious, and non-advisory.

## Safety Rules

- No brokerage login.
- No credential storage.
- No automated trading.
- No direct buy/sell commands.
- No guaranteed return language.
- No price prediction framing.
- No vector database yet.
- No model training yet.
- No external LLM or key changes without explicit approval.
- Preserve user privacy and avoid logging sensitive holdings unnecessarily.

Preferred wording:

- review
- monitor
- concentration
- risk threshold
- rebalance scenario
- heuristic estimate
- not financial advice

## Non-Goals

- No brokerage or custodian integration
- No account scraping
- No embeddings or vector memory
- No cloud memory infrastructure
- No direct trading execution
- No fully autonomous portfolio agent
- No paid data-source dependency for this milestone

## Recommended Implementation Order

1. Build `PortfolioContextBuilder` using existing saved/current workspace data.
2. Add backend schema and orchestration for portfolio-aware chat.
3. Reuse existing portfolio intelligence, stress-test, and signal evidence where available.
4. Add frontend **Ask About My Portfolio** panel.
5. Add starter question chips and evidence-used indicators.
6. Add backend and frontend tests.
7. Update README/demo notes after implementation stabilizes.

## Assumptions

- Local saved/current workspace support remains the primary memory source.
- Existing portfolio intelligence and stress-test outputs are sufficiently stable to reuse as evidence.
- Signal evidence remains deterministic and optional.
- Privacy and demo simplicity are more important than long-term memory sophistication in this phase.

## Risks Requiring Yuni Approval

Stop and ask Yuni before adding:

- external LLM API calls
- paid APIs
- model training
- embeddings or vector databases
- broker APIs or brokerage scraping
- cloud-hosted memory or account sync
- any secret-bearing integration
