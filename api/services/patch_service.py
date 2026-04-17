from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


class PatchApplicationError(Exception):
    """Raised when a patch payload cannot be applied."""


def apply_schedule_patches(schedule_json: Dict[str, Any], patch_payload: Dict[str, Any]) -> Dict[str, Any]:
    patches = patch_payload.get("patches")
    if not isinstance(patches, list):
        raise PatchApplicationError("Patch payload missing 'patches' list")

    updated = deepcopy(schedule_json)
    instances = updated.get("instances")
    if not isinstance(instances, list):
        raise PatchApplicationError("schedule_json.instances must be a list")

    for patch in patches:
        if not isinstance(patch, dict):
            raise PatchApplicationError("Each patch must be an object")
        op = patch.get("op")
        if op == "update_operation":
            _apply_update_operation(updated, patch)
        elif op == "add_operation":
            _apply_add_operation(updated, patch)
        elif op == "delete_operation":
            _apply_delete_operation(updated, patch)
        elif op == "update_job":
            _apply_update_job(updated, patch)
        else:
            raise PatchApplicationError(f"Unsupported patch op '{op}'")

    updated_instances = updated.get("instances", [])
    if isinstance(updated_instances, list):
        updated["J"] = len(updated_instances)
    return updated


def _find_job(schedule: Dict[str, Any], job_id: int) -> Dict[str, Any]:
    instances = schedule.get("instances", [])
    for job in instances:
        if isinstance(job, dict) and job.get("job_id") == job_id:
            return job
    raise PatchApplicationError(f"Job {job_id} not found")


def _find_operation(job: Dict[str, Any], op_id: int) -> Dict[str, Any]:
    operations = job.get("operations", [])
    for operation in operations:
        if isinstance(operation, dict) and operation.get("op_id") == op_id:
            return operation
    raise PatchApplicationError(f"Operation {op_id} not found in job {job.get('job_id')}")


def _apply_update_operation(schedule: Dict[str, Any], patch: Dict[str, Any]) -> None:
    job_id = patch.get("job_id")
    op_id = patch.get("op_id")
    fields = patch.get("set")
    if not isinstance(job_id, int) or not isinstance(op_id, int) or not isinstance(fields, dict):
        raise PatchApplicationError("update_operation requires integer job_id/op_id and a 'set' object")
    job = _find_job(schedule, job_id)
    operation = _find_operation(job, op_id)
    for key, value in fields.items():
        if key not in {"op_n", "re", "pre"}:
            raise PatchApplicationError(f"Unsupported field '{key}' in update_operation")
        operation[key] = value


def _apply_add_operation(schedule: Dict[str, Any], patch: Dict[str, Any]) -> None:
    job_id = patch.get("job_id")
    operation = patch.get("operation")
    if not isinstance(job_id, int) or not isinstance(operation, dict):
        raise PatchApplicationError("add_operation requires integer job_id and an operation object")
    required_fields = {"op_id", "op_n", "re", "pre"}
    if not required_fields.issubset(operation.keys()):
        missing = required_fields - set(operation.keys())
        raise PatchApplicationError(f"operation missing required fields: {', '.join(sorted(missing))}")
    job = _find_job(schedule, job_id)
    operations = job.setdefault("operations", [])
    existing_ids = {op.get("op_id") for op in operations if isinstance(op, dict)}
    if operation.get("op_id") in existing_ids:
        raise PatchApplicationError(f"Operation id {operation.get('op_id')} already exists in job {job_id}")
    operations.append(operation)


def _apply_delete_operation(schedule: Dict[str, Any], patch: Dict[str, Any]) -> None:
    job_id = patch.get("job_id")
    op_id = patch.get("op_id")
    if not isinstance(job_id, int) or not isinstance(op_id, int):
        raise PatchApplicationError("delete_operation requires integer job_id and op_id")
    job = _find_job(schedule, job_id)
    operations = job.get("operations", [])
    original_len = len(operations)
    job["operations"] = [op for op in operations if op.get("op_id") != op_id]
    if len(job.get("operations", [])) == original_len:
        raise PatchApplicationError(f"Operation {op_id} not found in job {job_id}")


def _apply_update_job(schedule: Dict[str, Any], patch: Dict[str, Any]) -> None:
    job_id = patch.get("job_id")
    fields = patch.get("set")
    if not isinstance(job_id, int) or not isinstance(fields, dict):
        raise PatchApplicationError("update_job requires integer job_id and a 'set' object")
    job = _find_job(schedule, job_id)
    for key, value in fields.items():
        if key not in {"job_n"}:
            raise PatchApplicationError(f"Unsupported field '{key}' in update_job")
        job[key] = value
