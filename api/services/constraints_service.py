from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from api.services.run_registry import RUN_REGISTRY


class ConstraintServiceError(RuntimeError):
    """Raised when constraint checks fail."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path_like: str) -> Path:
    path = Path(path_like)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def check_deadlines(deadlines: List[float], run_id: Optional[str] = None) -> Dict[str, Any]:
    """Persist deadlines and simple run metrics for offline inspection."""

    if run_id is None:
        raise ConstraintServiceError("run_id is required to evaluate deadlines")

    run = RUN_REGISTRY.get(run_id)
    results = (run.get("results") or {}).get("runs", [])
    if not results:
        raise ConstraintServiceError(f"Run {run_id} has no solution pool data")

    ts = time.strftime("%Y%m%d_%H%M%S")
    deadlines_path = _resolve(f"solution_pools/deadlines_{ts}.npy")
    deadlines_array = np.array(deadlines, dtype=float)
    np.save(deadlines_path, deadlines_array)

    pool_rows = []
    for idx, entry in enumerate(results, start=1):
        makespan = float(entry.get("makespan", 0.0))
        deadline_met = any(makespan <= d for d in deadlines_array)
        pool_rows.append(
            {
                "instance_id": idx,
                "makespan": makespan,
                "deadline_met": bool(deadline_met),
                "pool_csv": entry.get("pool_csv"),
            }
        )

    pool_df = pd.DataFrame(pool_rows)
    pool_path = _resolve(f"solution_pools/deadline_report_{ts}.csv")
    pool_df.to_csv(pool_path, index=False)

    return {
        "deadlines_path": str(deadlines_path),
        "pool_path": str(pool_path),
        "valid_solutions": int(pool_df["deadline_met"].sum()),
    }


def extract_precedence_matrix(schedule_json: Dict[str, Any]) -> Optional[np.ndarray]:
    try:
        n_jobs = schedule_json["J"]
        matrix = np.zeros((n_jobs, n_jobs), dtype=int)
        for job in schedule_json.get("instances", []):
            job_id = job.get("job_id", 0) - 1
            for op in job.get("operations", []):
                for pre_op_id in op.get("pre", []) or []:
                    for peer_job in schedule_json.get("instances", []):
                        for peer_op in peer_job.get("operations", []):
                            if peer_op.get("op_id") == pre_op_id:
                                pre_job_id = peer_job.get("job_id", 0) - 1
                                if pre_job_id != job_id:
                                    matrix[pre_job_id, job_id] = 1
        return matrix if np.any(matrix) else None
    except Exception as exc:
        raise ConstraintServiceError(f"Failed to extract precedence matrix: {exc}") from exc


def check_precedence(schedule_json: Dict[str, Any]) -> Dict[str, Any]:
    matrix = extract_precedence_matrix(schedule_json)
    if matrix is None:
        return {"precedence_matrix": None, "precedence_path": None}

    ts = time.strftime("%Y%m%d_%H%M%S")
    path = _resolve(f"solution_pools/precedence_matrix_{ts}.npy")
    np.save(path, matrix)
    return {"precedence_matrix": matrix.tolist(), "precedence_path": str(path)}
