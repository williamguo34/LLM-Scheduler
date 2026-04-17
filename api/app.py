from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from fjsp_app.backend.transform import json_to_tables, tables_to_json

from api.models import (
    AlgorithmName,
    AssetsListResponse,
    ConstraintDeadlineRequest,
    ConstraintDeadlineResponse,
    JSONDiffRequest,
    LLMGenerateRequest,
    LLMUpdateRequest,
    CSVAdjustmentRequest,
    LLMDecisionRequest,
    PrecedenceRequest,
    PrecedenceResponse,
    ScheduleSchemaResponse,
    ScheduleTransformDirection,
    ScheduleTransformRequest,
    SolverRunRequest,
    SolverRunSummary,
)
from api.services.assets_service import (
    list_gantt_charts,
    list_model_weights,
    list_solution_pools,
)
from api.services.constraints_service import (
    ConstraintServiceError,
    check_deadlines,
    check_precedence,
)
from api.services.diff_service import json_diff, table_diff
from api.services.llm_service import (
    LLMServiceError,
    decide_update_route,
    generate_schedule_json,
    load_schedule_schema,
    update_schedule_json,
    update_schedule_patch,
    update_solution_csv_llm,
)
from api.services.run_registry import RUN_REGISTRY
from api.services.solver_service import SolverServiceError, solve_with_iaoa_gns, solve_with_ppo


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_asset_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / raw_path
    path = path.resolve()
    if PROJECT_ROOT not in path.parents and path != PROJECT_ROOT:
        raise HTTPException(status_code=403, detail="Path outside project root is not allowed")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    return path


app = FastAPI(title="FJSP Scheduling API", version="0.1.0")


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/schedules/generate")
def api_generate_schedule(request: LLMGenerateRequest) -> Dict[str, Any]:
    try:
        schedule = generate_schedule_json(
            user_message=request.user_message,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return {"schedule_json": schedule}
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/schedules/update")
def api_update_schedule(request: LLMUpdateRequest) -> Dict[str, Any]:
    try:
        schedule = update_schedule_json(
            current_json=request.current_json,
            instruction=request.instruction,
            previous_messages=[msg.dict() for msg in request.previous_messages or []],
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return {"schedule_json": schedule}
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/schedules/update_patch")
def api_update_schedule_patch(request: LLMUpdateRequest) -> Dict[str, Any]:
    try:
        schedule = update_schedule_patch(
            current_json=request.current_json,
            instruction=request.instruction,
            previous_messages=[msg.dict() for msg in request.previous_messages or []],
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return {"schedule_json": schedule}
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/schedules/csv-adjustment")
def api_adjust_csv(request: CSVAdjustmentRequest) -> Dict[str, Any]:
    try:
        df = update_solution_csv_llm(
            csv_path=request.csv_path,
            instruction=request.instruction,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = Path(request.csv_path).with_name(f"{Path(request.csv_path).stem}_llm_updated_{ts}.csv")
        df.to_csv(out_path, index=False)
        preview = df.head(20).to_dict(orient="records")
        return {"csv_path": str(out_path), "preview": preview}
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/schedules/schema", response_model=ScheduleSchemaResponse)
def api_schedule_schema() -> ScheduleSchemaResponse:
    schema = load_schedule_schema()
    return ScheduleSchemaResponse(schema=schema)


@app.post("/api/schedules/transform")
def api_transform_schedule(request: ScheduleTransformRequest) -> Dict[str, Any]:
    if request.direction == ScheduleTransformDirection.to_tables:
        tables = json_to_tables(request.payload)
        serialized: List[Dict[str, Any]] = []
        for job_id, job_name, df in tables:
            serialized.append(
                {
                    "job_id": job_id,
                    "job_name": job_name,
                    "rows": df.to_dict(orient="records"),
                }
            )
        return {"tables": serialized}
    if request.direction == ScheduleTransformDirection.from_tables:
        if not request.original_json:
            raise HTTPException(status_code=400, detail="original_json is required for from_tables transformation")
        tables_payload = request.payload.get("tables", [])
        tables = []
        for table in tables_payload:
            df = pd.DataFrame(table.get("rows", []))
            tables.append((table.get("job_id"), table.get("job_name"), df))
        schedule = tables_to_json(tables, request.original_json)
        return {"schedule_json": schedule}
    raise HTTPException(status_code=400, detail="Unsupported transform direction")


@app.post("/api/diff/json")
def api_diff_json(request: JSONDiffRequest) -> Dict[str, Any]:
    diff_text = json_diff(request.current_json, request.proposed_json)
    return {"diff": diff_text}


@app.post("/api/diff/table")
def api_diff_table(request: JSONDiffRequest) -> Dict[str, Any]:
    changes = table_diff(request.current_json, request.proposed_json)
    return {"changes": changes}


@app.post("/api/llm/route")
def api_decide_route(request: LLMDecisionRequest) -> Dict[str, str]:
    try:
        decision = decide_update_route(
            instruction=request.instruction,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return {"decision": decision}
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/solvers/run", response_model=SolverRunSummary)
def api_run_solver(request: SolverRunRequest) -> SolverRunSummary:
    config: Dict[str, Any]
    if request.algorithm == AlgorithmName.ppo:
        config = request.ppo.model_dump() if request.ppo else {}
    else:
        config = request.iaoa_gns.model_dump() if request.iaoa_gns else {}

    run_id = RUN_REGISTRY.create(request.algorithm.value, config)
    try:
        RUN_REGISTRY.update(run_id, status="running")
        if request.algorithm == AlgorithmName.ppo:
            if request.ppo is None:
                raise HTTPException(status_code=400, detail="ppo configuration required")
            results = solve_with_ppo(request.schedule_json, request.ppo)
        else:
            if request.iaoa_gns is None:
                raise HTTPException(status_code=400, detail="iaoa_gns configuration required")
            results = solve_with_iaoa_gns(request.schedule_json, request.iaoa_gns)
        RUN_REGISTRY.update(run_id, status="completed", results=results)
    except SolverServiceError as exc:
        RUN_REGISTRY.update(run_id, status="failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))

    record = RUN_REGISTRY.get(run_id)
    return SolverRunSummary(
        run_id=run_id,
        algorithm=request.algorithm,
        status=record["status"],
        created_at=record["created_at"],
        config=config,
        results=record.get("results"),
        error=record.get("error"),
    )


@app.get("/api/solvers/run/{run_id}", response_model=SolverRunSummary)
def api_get_solver(run_id: str) -> SolverRunSummary:
    try:
        record = RUN_REGISTRY.get(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

    return SolverRunSummary(
        run_id=record["run_id"],
        algorithm=AlgorithmName(record["algorithm"]),
        status=record["status"],
        created_at=record["created_at"],
        config=record.get("config", {}),
        results=record.get("results"),
        error=record.get("error"),
    )


@app.post("/api/constraints/deadlines", response_model=ConstraintDeadlineResponse)
def api_check_deadlines(request: ConstraintDeadlineRequest) -> ConstraintDeadlineResponse:
    try:
        result = check_deadlines(request.deadlines, request.run_id)
        return ConstraintDeadlineResponse(**result)
    except ConstraintServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/constraints/precedence", response_model=PrecedenceResponse)
def api_check_precedence(request: PrecedenceRequest) -> PrecedenceResponse:
    try:
        result = check_precedence(request.schedule_json)
        return PrecedenceResponse(**result)
    except ConstraintServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/assets/solution-pools", response_model=AssetsListResponse)
def api_list_solution_pools() -> AssetsListResponse:
    return AssetsListResponse(items=list_solution_pools())


@app.get("/api/assets/gantt-charts", response_model=AssetsListResponse)
def api_list_gantt_charts() -> AssetsListResponse:
    return AssetsListResponse(items=list_gantt_charts())


@app.get("/api/assets/models", response_model=AssetsListResponse)
def api_list_model_weights() -> AssetsListResponse:
    return AssetsListResponse(items=list_model_weights())


@app.get("/api/assets/file")
def api_get_asset_file(path: str) -> FileResponse:
    resolved = _resolve_asset_path(path)
    return FileResponse(resolved, filename=resolved.name)


@app.get("/api/assets/preview")
def api_preview_asset(path: str, max_bytes: int = 20000) -> Dict[str, Any]:
    resolved = _resolve_asset_path(path)
    # Basic guard against binary previews
    if resolved.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
        raise HTTPException(status_code=400, detail="Image previews should be requested via /api/assets/file")

    with resolved.open("rb") as handle:
        chunk = handle.read(max(1024, min(max_bytes, 1_000_000)))
    file_size = resolved.stat().st_size
    truncated = file_size > len(chunk)
    content = chunk.decode("utf-8", errors="replace")
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        mime_type = "application/json"
    elif suffix == ".csv":
        mime_type = "text/csv"
    else:
        mime_type = "text/plain"
    return {
        "path": str(resolved),
        "content": content,
        "truncated": truncated,
        "mime_type": mime_type,
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("api.app:app", host=host, port=port, reload=os.environ.get("RELOAD", "0") == "1")
