# FJSP Scheduling API

This folder exposes a REST interface around the legacy Streamlit scheduling utilities so that a separate web UI (for example, a JavaScript frontend) can call into the scheduling engine.

## Structure

| File / Module | Purpose |
| --- | --- |
| `app.py` | FastAPI application wiring together all endpoints. Launch this module to start the HTTP server. |
| `models.py` | Pydantic request/response schemas shared by the API. |
| `services/llm_service.py` | Pure Python wrappers for LLM-based schedule generation, schedule updates, CSV tweaks, and route decisions. |
| `services/solver_service.py` | Back-end solver facade. Runs PPO or IAOA+GNS, captures artifacts, and returns summarized results. |
| `services/run_registry.py` | In-memory registry used to track solver runs. |
| `services/diff_service.py` | Helpers to compute JSON and table diffs for change review. |
| `services/constraints_service.py` | Functions to evaluate deadlines and precedence constraints using stored solver outputs. |
| `services/assets_service.py` | Lists solution pools, gantt charts, and available PPO weight directories. |
| `__init__.py` | Makes the package importable. |

## Prerequisites

- Python 3.9+
- Install dependencies (append to your project requirements as needed):
  ```bash
  pip install fastapi uvicorn pydantic pandas numpy openai
  ```
- The scheduling stack still depends on existing project modules (e.g., `Params`, `PPOwithValue`, `fjsp_app.*`). Run the API from the project root so those imports resolve.
- Set LLM credentials before calling generation endpoints:
  ```bash
  export OPENAI_API_KEY="sk-..."
  # optional if using a custom gateway
  export OPENAI_BASE_URL="https://models.inference.ai.azure.com"
  ```

## Running the Server

From the `Effisal_LLM` project root:

```bash
uvicorn api.app:app --reload
```

By default the server listens on `http://127.0.0.1:8000`. The module also supports direct execution (`python -m api.app`).

## Key Endpoints

All endpoints are rooted under `/api` unless noted otherwise. Refer to `app.py` for complete payload schemas.

### Health
- `GET /health` — Basic readiness probe.

### Schedule Authoring
- `POST /api/schedules/generate` — Create an initial schedule JSON from natural language.
- `POST /api/schedules/update` — Apply structural updates to an existing schedule JSON.
- `POST /api/schedules/csv-adjustment` — Ask the LLM to edit a solution pool CSV locally.
- `GET /api/schedules/schema` — Fetch the canonical FJSP JSON schema.
- `POST /api/schedules/transform` — Convert schedule JSON to/from table-friendly data for UI editors.
- `POST /api/llm/route` — Decide whether to run a schedule update or CSV adjustment based on user intent.

### Diffs & Validation
- `POST /api/diff/json` — Unified text diff between current and proposed JSON.
- `POST /api/diff/table` — Structured row-by-row comparison for table views.

### Solver Execution
- `POST /api/solvers/run` — Run either PPO or IAOA+GNS (specify configuration in body). Returns a run record with results and artifacts.
- `GET /api/solvers/run/{run_id}` — Retrieve status/results for a previously started run.

### Constraints & Reports
- `POST /api/constraints/deadlines` — Evaluate solver outputs against deadlines (requires `run_id`).
- `POST /api/constraints/precedence` — Compute precedence matrix from a schedule JSON.

### Asset Listing
- `GET /api/assets/solution-pools`
- `GET /api/assets/gantt-charts`
- `GET /api/assets/models`

## Typical Flow

1. **Generate**: POST `/api/schedules/generate` with the user prompt to obtain a schedule JSON.
2. **Iterate**: POST `/api/schedules/update` (or `/api/llm/route` first to decide CSV vs JSON) to modify the schedule. Use `/api/diff/*` endpoints to show changes.
3. **Solve**: POST `/api/solvers/run` with the schedule and solver configuration. Poll `/api/solvers/run/{run_id}` for results.
4. **Review**: Fetch gantt charts, solution CSVs, or run summaries via `/api/assets/*`.
5. **Validate**: POST `/api/constraints/deadlines` or `/api/constraints/precedence` for further analysis.

Adapt these endpoints to your frontend; each responds with JSON payloads ready for consumption.
