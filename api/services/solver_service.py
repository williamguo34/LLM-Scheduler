from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import torch

from Params import configs
from PPOwithValue import PPO
from validation_csv import enrich_solution_csv, generate_gantt_from_df, validate

from fjsp_app.backend.transform import openai_json_to_npy
from fjsp_app.backend.validation import validate_schedule_for_ppo
from fjsp_app.core.iaoa_gns import IAOAGNSAlgorithm, IAOAConfig
from fjsp_app.core.problem_adapter import (
    solution_to_yuchu_format,
    yuchu_json_to_problem_instance,
)

from api.models import IAOAGNSRunConfig, PPORunConfig


class SolverServiceError(RuntimeError):
    """Raised when a solver execution fails."""


@dataclass
class RunArtifact:
    run_number: int
    makespan: float
    gantt_file: Optional[str]
    pool_csv: Optional[str]
    pool_rows: int

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class SnapshotArtifacts:
    pool_csv: str
    instance_json: str
    instance_npy: Optional[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path_like: str) -> Path:
    path = Path(path_like)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_ppo_policy(weights_dir: str) -> PPO:
    weights_path = _resolve(weights_dir)
    job_path = weights_path / "policy_job.pth"
    mch_path = weights_path / "policy_mch.pth"
    if not job_path.exists() or not mch_path.exists():
        raise SolverServiceError(f"Missing PPO weights in {weights_path}")

    ppo = PPO(
        configs.lr,
        configs.gamma,
        configs.k_epochs,
        configs.eps_clip,
        n_j=10,
        n_m=10,
        num_layers=configs.num_layers,
        neighbor_pooling_type=configs.neighbor_pooling_type,
        input_dim=configs.input_dim,
        hidden_dim=configs.hidden_dim,
        num_mlp_layers_feature_extract=configs.num_mlp_layers_feature_extract,
        num_mlp_layers_actor=configs.num_mlp_layers_actor,
        hidden_dim_actor=configs.hidden_dim_actor,
        num_mlp_layers_critic=configs.num_mlp_layers_critic,
        hidden_dim_critic=configs.hidden_dim_critic,
    )
    map_location = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ppo.policy_job.load_state_dict(torch.load(job_path, map_location=map_location, weights_only=True))
    ppo.policy_mch.load_state_dict(torch.load(mch_path, map_location=map_location, weights_only=True))
    return ppo


def _prepare_tensor(npy_data: np.ndarray) -> torch.FloatTensor:
    npy = np.array(npy_data)
    if npy.ndim == 3:
        npy = npy.reshape(1, *npy.shape)
    return torch.FloatTensor(npy)


def _normalize_artifact_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        return str(_resolve(path))
    except Exception:
        try:
            return str(Path(path).resolve())
        except Exception:
            return path


def _collect_solution_pool(run_number: int, makespan: float) -> RunArtifact:
    src = Path("solution_pool.csv")
    pool_csv = None
    pool_rows = 0
    if src.exists():
        _ensure_dir(_resolve("solution_pools"))
        ts = time.strftime("%Y%m%d_%H%M%S")
        pool_csv = _resolve(f"solution_pools/solution_pool_{ts}_run{run_number}.csv")
        try:
            shutil.move(str(src), pool_csv)
            try:
                pool_rows = len(pd.read_csv(pool_csv))
            except Exception:
                pool_rows = 0
        except Exception as exc:
            raise SolverServiceError(f"Failed to persist solution pool: {exc}")
    gantt_file = f"gantt_charts/run_{run_number}_gantt_chart_instance_1.png"
    gantt_path = _resolve(gantt_file)
    return RunArtifact(
        run_number=run_number,
        makespan=makespan,
        gantt_file=str(gantt_path) if gantt_path.exists() else None,
        pool_csv=str(pool_csv) if pool_csv else None,
        pool_rows=pool_rows,
    )


def _save_solution_snapshot(solution_pool: List[RunArtifact], schedule_json: Dict[str, Any]) -> SnapshotArtifacts:
    _ensure_dir(_resolve("solution_pools"))
    ts = time.strftime("%Y%m%d_%H%M%S")
    pool_df = pd.DataFrame([a.__dict__ for a in solution_pool])
    pool_csv = _resolve(f"solution_pools/instance_{ts}.csv")
    pool_df.to_csv(pool_csv, index=False)

    instance_json_path = _resolve(f"solution_pools/instance_{ts}.json")
    with instance_json_path.open("w", encoding="utf-8") as handle:
        json.dump(schedule_json, handle, indent=2)

    npy = openai_json_to_npy(schedule_json)
    npy_path: Optional[Path] = None
    if npy is not None:
        npy_path = _resolve(f"solution_pools/instance_{ts}.npy")
        np.save(npy_path, npy)

    return SnapshotArtifacts(
        pool_csv=str(pool_csv),
        instance_json=str(instance_json_path),
        instance_npy=str(npy_path) if npy_path else None,
        timestamp=ts,
    )


def solve_with_ppo(schedule_json: Dict[str, Any], config: PPORunConfig) -> Dict[str, Any]:
    valid, message = validate_schedule_for_ppo(schedule_json)
    if not valid:
        raise SolverServiceError(f"Schedule validation failed: {message}")

    npy_data = openai_json_to_npy(schedule_json)
    if npy_data is None:
        raise SolverServiceError("Failed to convert schedule JSON to numpy format")

    tensor = _prepare_tensor(npy_data)
    results: List[float] = []
    artifacts: List[RunArtifact] = []

    for run in range(1, config.runs + 1):
        ppo = _load_ppo_policy(config.model_weights_dir)
        run_results = validate([tensor], 1, ppo.policy_job, ppo.policy_mch, run_number=run)
        if not run_results:
            raise SolverServiceError(f"PPO run {run} produced no results")
        makespan = float(run_results[0])
        results.append(makespan)
        artifact = _collect_solution_pool(run, makespan)
        artifacts.append(artifact)

    snapshot = _save_solution_snapshot(artifacts, schedule_json)
    summary = {
        "best": min(results),
        "average": mean(results),
        "worst": max(results),
    }

    enriched = []
    for artifact in artifacts:
        artifact.pool_csv = _normalize_artifact_path(artifact.pool_csv)
        artifact.gantt_file = _normalize_artifact_path(artifact.gantt_file)
        if artifact.pool_csv:
            df = enrich_solution_csv(artifact.pool_csv, schedule_json)
            if df is not None:
                gantt_output = generate_gantt_from_df(
                    df,
                    title=f"Run {artifact.run_number} - Makespan: {artifact.makespan}",
                )
            else:
                gantt_output = None
        else:
            gantt_output = None
        gantt_output = _normalize_artifact_path(gantt_output)
        enriched.append({
            **artifact.to_dict(),
            "gantt_generated": gantt_output,
        })

    return {
        "algorithm": "ppo",
        "summary": summary,
        "makespans": results,
        "runs": enriched,
        "snapshot": snapshot.to_dict(),
    }


def solve_with_iaoa_gns(schedule_json: Dict[str, Any], config: IAOAGNSRunConfig) -> Dict[str, Any]:
    problem = yuchu_json_to_problem_instance(schedule_json)
    algorithm = IAOAGNSAlgorithm(
        IAOAConfig(
            pop_size=config.population_size,
            max_iterations=config.max_iterations,
        )
    )

    results: List[float] = []
    artifacts: List[RunArtifact] = []

    for run in range(1, config.num_runs + 1):
        solution = algorithm.solve(problem, verbose=False, timeout=config.timeout_seconds)
        makespan = float(solution.makespan)
        results.append(makespan)

        solution_data = solution_to_yuchu_format(solution, problem, schedule_json)
        df = pd.DataFrame(solution_data["schedule"])
        _ensure_dir(_resolve("solution_pools"))
        ts = time.strftime("%Y%m%d_%H%M%S")
        pool_csv = _resolve(f"solution_pools/iaoa_solution_pool_{ts}_run{run}.csv")
        df.to_csv(pool_csv, index=False)

        gantt_output = None
        if not df.empty:
            df_enriched = enrich_solution_csv(pool_csv, schedule_json)
            if df_enriched is not None:
                gantt_output = generate_gantt_from_df(
                    df_enriched,
                    title=f"IAOA+GNS Run {run} - Makespan: {makespan}",
                )

        gantt_output = _normalize_artifact_path(gantt_output)

        artifact = RunArtifact(
            run_number=run,
            makespan=makespan,
            gantt_file=gantt_output,
            pool_csv=str(pool_csv),
            pool_rows=len(df),
        )
        artifacts.append(artifact)

    snapshot = _save_solution_snapshot(artifacts, schedule_json)
    summary = {
        "best": min(results),
        "average": mean(results),
        "worst": max(results),
    }

    return {
        "algorithm": "iaoa_gns",
        "summary": summary,
        "makespans": results,
        "runs": [artifact.to_dict() for artifact in artifacts],
        "snapshot": snapshot.to_dict(),
    }
