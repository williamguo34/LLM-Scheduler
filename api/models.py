from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class LLMGenerateRequest(BaseModel):
    user_message: str = Field(..., description="Natural-language description of the scheduling problem.")
    model: Optional[str] = Field(None, description="OpenAI-compatible model name.")
    api_key: Optional[str] = Field(None, description="API key for the LLM provider.")
    base_url: Optional[str] = Field(None, description="Base URL for the LLM provider.")


class LLMUpdateRequest(BaseModel):
    current_json: Dict[str, Any]
    instruction: str
    previous_messages: Optional[List[Message]] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LLMDecisionRequest(BaseModel):
    instruction: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class CSVAdjustmentRequest(BaseModel):
    csv_path: str = Field(..., description="Path to the solution pool CSV to adjust.")
    instruction: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ScheduleSchemaResponse(BaseModel):
    schema: Dict[str, Any]


class ScheduleTransformDirection(str, Enum):
    to_tables = "to_tables"
    from_tables = "from_tables"


class ScheduleTransformRequest(BaseModel):
    direction: ScheduleTransformDirection
    payload: Dict[str, Any]
    original_json: Optional[Dict[str, Any]] = None


class JSONDiffRequest(BaseModel):
    current_json: Dict[str, Any]
    proposed_json: Dict[str, Any]


class TableDiffItem(BaseModel):
    job_id: Any
    job_name: Optional[str] = None
    current_rows: List[Dict[str, Any]]
    proposed_rows: List[Dict[str, Any]]


class TableDiffResponse(BaseModel):
    changes: List[TableDiffItem]


class AlgorithmName(str, Enum):
    ppo = "ppo"
    iaoa_gns = "iaoa_gns"


class PPORunConfig(BaseModel):
    model_weights_dir: str = Field(
        "saved_network/FJSP_J10M10/best_value000",
        description="Directory containing PPO policy weights.",
    )
    runs: int = Field(1, ge=1, le=10)


class IAOAGNSRunConfig(BaseModel):
    population_size: int = Field(30, ge=5, le=200)
    max_iterations: int = Field(50, ge=10, le=500)
    num_runs: int = Field(1, ge=1, le=10)
    timeout_seconds: float = Field(600.0, gt=0)
<<<<<<< HEAD
=======
    pool_size: int = Field(10, ge=1, le=20, description="Number of solutions to return from final population")
    use_final_population: bool = Field(True, description="Return top-K from final population (single run only)")
>>>>>>> 225dbaf0fb8c557e0741a478ccd094a3b257cba8


class SolverRunRequest(BaseModel):
    schedule_json: Dict[str, Any]
    algorithm: AlgorithmName
    ppo: Optional[PPORunConfig] = None
    iaoa_gns: Optional[IAOAGNSRunConfig] = None


class SolverRunSummary(BaseModel):
    run_id: str
    algorithm: AlgorithmName
    status: str
    created_at: datetime
    config: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ConstraintDeadlineRequest(BaseModel):
    run_id: Optional[str] = Field(None, description="Run identifier to reuse existing solution pool.")
    deadlines: List[float] = Field(..., description="Deadlines to evaluate.")


class ConstraintDeadlineResponse(BaseModel):
    deadlines_path: str
    pool_path: str
    valid_solutions: int


class PrecedenceRequest(BaseModel):
    schedule_json: Dict[str, Any]


class PrecedenceResponse(BaseModel):
    precedence_matrix: Optional[List[List[int]]]
    precedence_path: Optional[str]


class AssetsListResponse(BaseModel):
    items: List[Dict[str, Any]]
