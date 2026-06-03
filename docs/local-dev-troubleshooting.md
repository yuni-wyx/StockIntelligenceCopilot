# Local Development Troubleshooting

This project has previously caused severe local memory spikes when opening
`localhost:3000` during frontend development. In the worst case, the Mac became
unresponsive.

## What Happened

The spike appeared to come from the Next.js development toolchain rather than a
React application runtime loop. The risky combination was:

- Next.js 16
- Turbopack dev mode
- `reactCompiler: true`
- `nxnode.bin` / `next-server` memory growth

Static review of the root page did not show an automatic fetch, stream startup,
localStorage hydration loop, or React infinite render loop. Treat this as a dev
toolchain stability issue unless new evidence points elsewhere.

## Current Safer Setup

The frontend is currently configured for safer local testing:

- `reactCompiler: false` in `frontend/stock-ui/next.config.ts`
- `npm run dev` uses `next dev --webpack`

Do not re-enable Turbopack or React Compiler for debugging unless the goal is
explicitly to test those tools.

## Safe Local Testing Process

Do not open the browser first.

1. Start the frontend dev server:

   ```bash
   cd frontend/stock-ui
   npm run dev
   ```

2. Check the root page with curl:

   ```bash
   curl -I http://localhost:3000
   ```

3. Check the copilot route with curl:

   ```bash
   curl -I http://localhost:3000/copilot
   ```

4. Watch Activity Monitor while running the curl checks.

5. Only after the curl checks behave normally, open Safari Private Window and
   visit:

   ```text
   http://localhost:3000
   ```

## Memory Expectations

Normal local dev memory can be noisy. It is acceptable if `next-server` rises
from about 500 MB to about 700 MB during compilation and then drops back or
stabilizes.

Danger signs:

- `next-server`, `node`, or `nxnode.bin` continuously rises into multiple GB
- memory does not drop after compilation finishes
- the Mac UI starts freezing or swapping heavily

If any danger sign appears, stop the dev server before opening additional
routes.

## Codex Rules For This Project

Codex must follow these defaults for local frontend debugging:

- Do not open `localhost:3000` automatically.
- Do not use browser automation unless explicitly requested.
- Do not run Playwright for local debugging.
- Use curl-based checks before opening a browser.
- Do not use Turbopack or React Compiler for debugging unless explicitly
  testing them.

