from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _collect_files(folder: str, extensions: List[str] | None = None) -> List[Dict[str, str]]:
    base = _project_root() / folder
    if not base.exists():
        return []
    items: List[Dict[str, str]] = []
    for entry in sorted(base.iterdir()):
        if entry.is_file():
            if not extensions or entry.suffix.lower() in extensions:
                items.append({"name": entry.name, "path": str(entry.resolve())})
        elif entry.is_dir():
            items.append({"name": entry.name + "/", "path": str(entry.resolve())})
    return items


def list_solution_pools() -> List[Dict[str, str]]:
    return _collect_files("solution_pools", extensions=[".csv", ".json", ".npy"])


def list_gantt_charts() -> List[Dict[str, str]]:
    return _collect_files("gantt_charts", extensions=[".png", ".jpg", ".jpeg"])


def list_model_weights() -> List[Dict[str, str]]:
    base = _project_root() / "saved_network"
    items: List[Dict[str, str]] = []
    if not base.exists():
        return items
    for directory in sorted(base.iterdir()):
        if directory.is_dir():
            items.append({"name": directory.name, "path": str(directory.resolve())})
    return items
