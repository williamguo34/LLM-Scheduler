from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4


class RunRegistry:
    """In-memory registry for solver runs."""

    def __init__(self) -> None:
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create(self, algorithm: str, config: Dict[str, Any]) -> str:
        run_id = uuid4().hex
        record = {
            "run_id": run_id,
            "algorithm": algorithm,
            "config": config,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "results": None,
            "error": None,
        }
        with self._lock:
            self._runs[run_id] = record
        return run_id

    def update(self, run_id: str, *, status: Optional[str] = None, results: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise KeyError(f"Unknown run_id: {run_id}")
            if status is not None:
                run["status"] = status
            if results is not None:
                run["results"] = results
            if error is not None:
                run["error"] = error

    def get(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise KeyError(f"Unknown run_id: {run_id}")
            return dict(run)

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._runs.items()}


RUN_REGISTRY = RunRegistry()
