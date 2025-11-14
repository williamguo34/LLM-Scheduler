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
from fjsp_app.core.iaoa_gns_pool import solve_with_pool, save_solution_pool_csv
from fjsp_app.core.problem_adapter import yuchu_json_to_problem_instance

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
    iaoa_config = IAOAConfig(
        pop_size=config.population_size,
        max_iterations=config.max_iterations,
    )

    # Solve with solution pool support
    pool_result = solve_with_pool(
        problem=problem,
        config=iaoa_config,
        num_runs=config.num_runs,
        pool_size=config.pool_size,
        use_final_population=config.use_final_population and config.num_runs == 1
    )

    results: List[float] = []
    artifacts: List[RunArtifact] = []
    _ensure_dir(_resolve("solution_pools"))
    ts = time.strftime("%Y%m%d_%H%M%S")

    # Handle single-run with final population vs multi-run
    if config.num_runs == 1 and config.use_final_population:
        # Single run: all solutions in one CSV
        solutions = pool_result['solutions']
        pool_csv_path = f"solution_pools/solution_pool_{ts}_run1.csv"
        pool_csv = _resolve(pool_csv_path)
        rows_written = save_solution_pool_csv(solutions, str(pool_csv), base_instance_id=1)
        
        # Generate one Gantt chart for all solutions (or first solution)
        gantt_output = None
        if pool_csv.exists():
            df_enriched = enrich_solution_csv(str(pool_csv), schedule_json)
            if df_enriched is not None and not df_enriched.empty:
                best_makespan = pool_result['best_makespan']
                gantt_output = generate_gantt_from_df(
                    df_enriched,
                    title=f"IAOA+GNS Pool (Best: {best_makespan:.2f})",
                )
        
        gantt_output = _normalize_artifact_path(gantt_output)
        
        # Create artifact for each solution (all share same CSV)
        for idx, solution in enumerate(solutions):
            makespan = float(solution.makespan)
            results.append(makespan)
            
            artifact = RunArtifact(
                run_number=1,
                makespan=makespan,
                gantt_file=gantt_output if idx == 0 else None,  # Only first solution gets gantt
                pool_csv=str(pool_csv),
                pool_rows=rows_written,
            )
            artifacts.append(artifact)
    else:
        # Multi-run: one CSV per run
        for run in range(config.num_runs):
            run_solutions = pool_result['solutions'][run:run+1] if config.num_runs > 1 else pool_result['solutions']
            solution = run_solutions[0]
            makespan = float(solution.makespan)
            results.append(makespan)
            
            pool_csv = _resolve(f"solution_pools/solution_pool_{ts}_run{run+1}.csv")
            rows_written = save_solution_pool_csv(run_solutions, str(pool_csv), base_instance_id=run+1)
            
            gantt_output = None
            if pool_csv.exists():
                df_enriched = enrich_solution_csv(str(pool_csv), schedule_json)
                if df_enriched is not None:
                    gantt_output = generate_gantt_from_df(
                        df_enriched,
                        title=f"IAOA+GNS Run {run+1} - Makespan: {makespan}",
                    )
            
            gantt_output = _normalize_artifact_path(gantt_output)
            
            artifact = RunArtifact(
                run_number=run + 1,
                makespan=makespan,
                gantt_file=gantt_output,
                pool_csv=str(pool_csv),
                pool_rows=rows_written,
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
