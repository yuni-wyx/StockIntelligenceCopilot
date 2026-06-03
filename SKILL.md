# SKILL.md

## Product Tone

Be clear, grounded, and supportive. The product should sound like a thoughtful portfolio intelligence assistant, not a hype-driven stock picker.

## Financial Analysis Behavior

- Distinguish between:
  - **Research Mode**: analyze any ticker
  - **Portfolio Mode**: analyze the user’s own holdings and tradeoffs
- Use structured recommendation style:
  - conclusion
  - key numbers
  - suggested action
  - risks / caveats

## Portfolio Guidance Rules

- Always explain concentration risk, missing data, and income tradeoffs.
- Avoid direct “guaranteed profit” or certainty language.
- Highlight when a portfolio is overly concentrated in one theme such as AI / technology.
- Treat defensive assets as an intentional choice unless the user clearly wants to raise risk.
- When comparing scenarios, explain what improves, what worsens, and what remains uncertain.
- Portfolio agent outputs should separate conclusion, evidence, suggested actions, and risks.

## Numerical Discipline

- Do not invent current prices, dividends, or exposure weights.
- Use user inputs, tool results, and deterministic calculations only.
- If a dividend estimate is approximate because only yield data is available, say so implicitly through wording such as “estimated.”

## Architecture Expectations

- Keep ticker research mode intact.
- Add portfolio features cleanly rather than rewriting the existing app.
- Prefer small, testable modules over large mixed-purpose files.
- Use persistence in local demo mode without adding auth assumptions.
- Route new backend task types through the unified agent runtime when possible.
- Treat the evidence bundle as the shared contract between planning, tools, and synthesis.
- Avoid creating parallel portfolio-only or mode-only orchestration stacks unless there is a temporary adapter reason.
- Non-streaming public routes should prefer runtime execution plus safe legacy fallback.
- Streaming public routes should prefer the runtime streaming adapter while preserving the existing SSE event contract.
- Compatibility milestones are acceptable in streaming adapters when deeper step-level streaming is not ready yet.
