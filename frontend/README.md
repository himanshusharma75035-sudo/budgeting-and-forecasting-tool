# OpenFP&A — Frontend

React 19 + Vite + TypeScript (strict) single-page app for the OpenFP&A budgeting and
forecasting tool. It talks to the FastAPI backend over `/api`.

## Prerequisites

- Node.js 20+ (Node 18.18+ may work, but 20 LTS is recommended for Vite 6)
- The backend running locally at `http://127.0.0.1:8000`

## Getting started

```bash
npm install
npm run dev
```

The dev server starts on http://localhost:5173. Vite proxies all `/api/*` requests to
`http://127.0.0.1:8000` (configured in `vite.config.ts`), so make sure the backend is up.

## Scripts

| Script              | Purpose                                  |
| ------------------- | ---------------------------------------- |
| `npm run dev`       | Start the Vite dev server                |
| `npm run build`     | Type-check (`tsc -b`) and build for prod |
| `npm run preview`   | Preview the production build             |
| `npm run typecheck` | Strict type-check only (`tsc --noEmit`)  |
| `npm run lint`      | ESLint over the project                  |
| `npm run test`      | Run the Vitest suite                     |

## Pages

| Route         | Page          | Status     | Notes                                                                 |
| ------------- | ------------- | ---------- | --------------------------------------------------------------------- |
| `/`           | Dashboard     | Functional | Static overview + navigation cards.                                   |
| `/import`     | Data Import   | Functional | Uploads CSV to `POST /api/uploads`; template download links.          |
| `/accounts`   | Accounts      | Functional | `GET /api/accounts`, table with loading/error states.                 |
| `/budgets`    | Budgets       | Functional | Form (react-hook-form) → `POST /api/budgets/run`; renders lines/total.|
| `/forecasts`  | Forecasts     | Functional | `POST /api/forecasts/run`; Recharts line + 95% interval band + scoreboard. |
| `/variance`   | Variance      | Functional | `POST /api/variance/compute`; colored F/U table + bar chart.          |

All pages are functional against the documented API. Response handling assumes the shapes in
`src/lib/types.ts`. If the backend evolves, update those types first.

## Project structure

```
src/
  main.tsx           React root, providers (Router + React Query)
  App.tsx            Route table + Nav
  index.css          Minimal styling
  components/Nav.tsx Navigation bar
  lib/
    api.ts           Typed fetch wrapper (apiGet / apiPost / uploadFile)
    types.ts         API request/response interfaces
    money.ts         formatMoney / formatPct
  pages/             One component per route
  pages/__tests__/   Vitest smoke test
```

## Notes

- Data fetching uses `@tanstack/react-query` v5.
- Charts use Recharts.
- This is a scaffold: forms keep payloads minimal and there is no auth layer yet.
