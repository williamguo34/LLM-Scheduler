# FJSP Frontend (Vite + React + TypeScript)

This SPA replaces the legacy Streamlit UI with a modular React implementation that talks to the FastAPI backend in `../api`. The current scaffold focuses on establishing layout, navigation, API clients, and state plumbing so that feature work can proceed page by page.

## Project Layout

```
frontend/
├─ public/            Static assets served by Vite
├─ src/
│  ├─ api/            Axios wrappers for backend endpoints
│  ├─ components/     Reusable UI building blocks (e.g., Sidebar)
│  ├─ hooks/          Custom React hooks (polling helpers, etc.)
│  ├─ pages/          Route-aligned view components
│  ├─ store/          Zustand global store for shared state
│  ├─ types/          Shared TypeScript interfaces
│  ├─ App.tsx         Shell composing sidebar + routed pages
│  └─ main.tsx        React/Vite bootstrap (router, StrictMode)
├─ package.json       Scripts + dependency manifest
├─ tsconfig*.json     TypeScript compiler settings
└─ vite.config.ts     Vite configuration (dev server, proxy)
```

## Implemented Functionality

- **Routing shell (`App.tsx`)** – Sets up a sidebar + main content area, wiring React Router paths for all seven major flows (Overview, Builder, Table Editor, Solver Hub, Constraints, Assets, Settings).
- **Sidebar navigation (`components/Sidebar.tsx`)** – Styled navigation list with active-route highlight so users can pivot between workflows without page reloads.
- **Global store (`store/useAppStore.ts`)** – Zustand store captures schedule JSON, pending changes, chat transcript, solver runs, and convenient actions for downstream components.
- **REST clients (`api/*.ts`)** – Typed wrappers around the new FastAPI endpoints (schedules, solver, diff, constraints, assets). These utilities centralize HTTP calls and payload shapes for reuse across pages.
- **Utility hook (`hooks/usePolling.ts`)** – Provides a reusable polling loop for solver run updates or long-lived operations once the backend integration is turned on.
- **Overview dashboard (`pages/OverviewPage.tsx`)** – Displays snapshot cards for the active schedule, pending updates, latest solver run, and recent chat history by reading from the store (ready to connect to live data).
- **Page placeholders** – Each of the remaining routes includes a structured layout, descriptive copy, and TODO call-outs so future work can drop in real widgets without rethinking the framing.

## Known Gaps vs Legacy Streamlit UI

| Streamlit Feature | Current Status in React Frontend | Notes |
| --- | --- | --- |
| Home onboarding (file upload, metrics) | Not implemented | Need file upload, JSON import, and schema metrics.
| Chat-driven builder with auto-apply/auto-solve toggles, pending change preview | Not implemented | Requires LLM chat panel, toggle controls, diff viewer (can reuse API `/schedules/update`, `/diff`).
| Table editor with per-job grid editing, normalization/validation flow | Placeholder only | Need data grid component, JSON↔table transforms via `/schedules/transform` and validation feedback.
| Solver Hub with PPO / IAOA+GNS controls, parameter sliders, result charts | Placeholder only | Must call `/solver/run` and `/solver/runs/:id`, add status/polling visuals, chart makespans.
| Constraint checks (deadlines, precedence) | Placeholder only | Wire to `/constraints/deadlines`, `/constraints/precedence` endpoints and render matrices/messages.
| Asset browser (solution pool listing, Gantt previews) | Placeholder only | Fetch from `/assets/solution-pools` and `/assets/gantt`, add download/view actions and image previews.
| Settings (API keys, model config persisted to backend session) | Placeholder only | Build forms connected to `/llm/config` (to be defined) or local storage; ensure secure handling.
| Session state reset / conversation management | Partial | Store exposes helpers, but UI triggers still needed.

## Outstanding Technical Tasks

- Replace the temporary inline styles with a design system (e.g., Tailwind, CSS Modules, or component library) once agreed upon.
- Implement error boundaries and loading states around the API client calls.
- Add tests (unit + integration) once key flows are built.
- Decide on auth/secrets strategy for API keys (context provider, secure storage).

## Getting Started

1. Install dependencies (already done): `npm install`
2. Launch dev server: `npm run dev`
3. During development the Vite proxy (configured in `vite.config.ts`) forwards requests under `/api` to the FastAPI app, keeping frontend and backend in sync.

## Health Check

- TypeScript and ESLint compile successfully after installing dependencies.
- Temporary handcrafted React type definitions (`src/types/react.d.ts`) have been removed now that official `@types/*` packages are installed.
- No runtime widgets are wired yet, so navigation works but pages show placeholder copy until integrations land.

These notes should serve as a living guide while we port each Streamlit flow into the new SPA architecture. Reach out if you want me to prioritize any specific page next.
