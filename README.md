# Effisal_LLM Project Guide

Effisal_LLM is a Flexible Job Shop Scheduling (FJSP) assistant that splits into two major layers:

- **`api/`** – a FastAPI service exposing the scheduling, optimisation, and validation capabilities that originally lived inside the Streamlit app.
- **`frontend/`** – a Vite + React single-page application that replaces the Streamlit UI and consumes the REST API.

This document explains the purpose of each layer, how they interact, and how you can run or extend them.

---

## 1. Backend API (`api/`)

### Purpose

The FastAPI service turns the scheduling toolkit into a set of HTTP endpoints. It wraps three large groups of functionality:

1. **Schedule authoring and iteration** – LLM-assisted generation, updates, and table transformations.
2. **Solver execution** – PPO RL solver and the new IAOA+GNS metaheuristic, with run tracking and artifact storage.
3. **Diagnostics and assets** – constraint checks, json/table diffs, and file listings for solution pools or gantt charts.

A detailedd module-by-module description already lives in [`api/README.md`](api/README.md).

### Key Files

| Path | Role |
| --- | --- |
| `api/app.py` | FastAPI app with all route definitions and CORS settings. |
| `api/models.py` | Pydantic schemas for request/response validation. |
| `api/services/` | Pure Python business logic grouped by concern (LLM, solver, diff, constraints, assets, run registry). |

The API module imports many of the original scheduling utilities from the project root (e.g. `Params.py`, `utils/`, `fjsp_app/backend/`). Run the service from the repository root so these modules resolve correctly.

### Running the API Locally

1. **Create/activate a Python environment** (3.9+ recommended).
2. **Install dependencies**. If you do not already track them elsewhere, install FastAPI and the known third-party packages:
   ```bash
   pip install fastapi uvicorn pydantic numpy pandas openai
   ```
3. **Export LLM credentials** if you want the generate/update endpoints to call an OpenAI-compatible service:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export OPENAI_BASE_URL="https://models.inference.ai.azure.com"  # optional override
   ```
4. **Start the server** from the project root:
   ```bash
   uvicorn api.app:app --reload --port 8000
   ```
   The API root is now available at `http://127.0.0.1:8000`. Swagger docs sit at `/docs`.

### Common Workflows

- **Generate a schedule** – `POST /api/schedules/generate` with a `user_message` prompt.
- **Iterate on a schedule** – `POST /api/schedules/update` (or go through `/api/llm/route` to choose JSON vs CSV adjustments) and inspect diffs via `/api/diff/*`.
- **Solve** – `POST /api/solvers/run` with the algorithm and configuration; poll `/api/solvers/run/{run_id}` until finished.
- **Validate** – `POST /api/constraints/deadlines` or `/api/constraints/precedence` using the run ID or schedule JSON.
- **Browse assets** – `GET /api/assets/solution-pools`, `/api/assets/gantt-charts`, `/api/assets/models` for listings the frontend can render.

See the API README for the full parameter list and expected payload shapes.

---

## 2. Frontend (`frontend/`)

### Purpose

The frontend is a SPA that mirrors the Streamlit navigation structure (Overview, Builder, Table Editor, Solver Hub, Constraints, Assets, Settings) but runs in the browser. It talks to the FastAPI backend through the axios clients under `src/api/`.

### Implemented Pieces

- **Application shell** (`src/App.tsx`) – Flex layout combining a persistent sidebar with routed page content using React Router.
- **Sidebar navigation** (`src/components/Sidebar.tsx`) – Emoji-labelled nav items for all seven workflows, with active route highlighting.
- **Global store** (`src/store/useAppStore.ts`) – Zustand state container for schedule JSON, pending changes, chat messages, solver runs, and helper actions.
- **REST clients** (`src/api/*.ts`) – Type-safe axios wrappers pointing at the FastAPI endpoints (schedules, solver, diff, constraints, assets).
- **Polling hook** (`src/hooks/usePolling.ts`) – Lightweight abstraction for periodic API polling (useful for solver run updates).
- **Overview dashboard** (`src/pages/OverviewPage.tsx`) – Renders top-level cards summarising the current schedule, pending updates, most recent solver run, and recent chat history.
- **Placeholder pages** for Builder, Table Editor, Solver Hub, Constraints, Assets, and Settings – Each provides layout scaffolding and descriptive copy so real widgets can drop in later without reworking navigation.

A more detailed breakdown of the frontend structure and outstanding work lives in [`frontend/README.md`](frontend/README.md).

### Local Development

```bash
cd frontend
npm install       # already done once, rerun after dependency changes
npm run dev       # starts Vite dev server on http://localhost:5173
```

The Vite proxy defined in `vite.config.ts` forwards `/api/*` calls to `http://127.0.0.1:8000`, so run the FastAPI server in parallel for a full-stack experience. Build for production with `npm run build`; the output lands in `dist/`.

### Feature Parity vs Streamlit

The SPA currently replicates navigation and state wiring but still needs UI widgets for several flows:

- File upload/onboarding cards for the Home page.
- Chat composer, auto-apply/auto-solve toggles, and diff preview in Problem Builder.
- Interactive table grid for manual editing with validation messaging in Table Editor.
- Solver configuration forms, execution buttons, and charting in Solver Hub.
- Constraint inspectors populated from API responses.
- Asset list with download actions and Gantt previews.
- Settings forms for API keys, model weights, and other preferences.

All necessary backend endpoints exist; the remaining work is purely UI integration.

---

## 3. Putting It Together

1. **Spin up the backend** – `uvicorn api.app:app --reload` from the project root.
2. **Run the frontend** – `npm run dev` inside `frontend/`. Navigate to `http://localhost:5173` to see the React app.
3. **Iterate** – Build components page by page, relying on the centralized axios clients and Zustand store. Use the existing placeholders as a starting point.
4. **Persist solver artifacts** – The backend reads/writes from directories like `solution_pools/`, `gantt_charts/`, and `saved_network/`. Make sure those paths exist when running solvers.

For production deployment you can host the FastAPI app (behind Uvicorn/Gunicorn) and serve the built frontend (`frontend/dist/`) through any static web server or as part of the same ASGI stack.

---

## 4. Additional Directories

- `fjsp_app/` – The legacy Streamlit implementation. Useful for reference while porting UI flows. The APIs reuse much of its core logic.
- `models/`, `utils/`, `PPOwithValue.py`, etc. – Low-level scheduling and solver modules called by the API services.
- `saved_network/` – Trained PPO weight directories referenced by the solver endpoints.
- `solution_pools/`, `gantt_charts/` – Output artifacts that the frontend will eventually surface.

---

## 5. Next Steps

- Prioritise porting the Problem Builder experience (chat + diff + auto-apply) since it drives most other flows.
- Add form components and data tables using your preferred UI library or custom styling.
- Expand automated tests once critical paths move out of placeholders.
- Document environment variables and solver weight requirements in more detail as they solidify.

With this structure in place, you can continue migrating the Streamlit functionality page by page while keeping a clean separation between backend services and the new web UI.
