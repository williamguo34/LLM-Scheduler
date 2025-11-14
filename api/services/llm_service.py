from __future__ import annotations

import json
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import OpenAI


DEFAULT_BASE_URL = "https://models.inference.ai.azure.com"
PROMPT_FILE = "prompt_openai.txt"
PROMPT_UPDATE_FILE = "prompt_for_update.txt"
SCHEMA_FILE = "schema_openai.txt"


class LLMServiceError(RuntimeError):
    """Raised when an LLM operation fails."""


logger = logging.getLogger(__name__)


def _extract_schedule_from_failed_generation(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    marker = "schedule_json"
    idx = text.find(marker)
    if idx == -1:
        return None
    idx = text.find("=", idx)
    if idx == -1:
        return None
    idx = text.find("{", idx)
    if idx == -1:
        return None
    brace_level = 0
    end = None
    for pos in range(idx, len(text)):
        char = text[pos]
        if char == "{":
            brace_level += 1
        elif char == "}":
            brace_level -= 1
            if brace_level == 0:
                end = pos + 1
                break
    if end is None:
        return None
    json_str = text[idx:end]
    try:
        return json.loads(json_str)
    except Exception:
        return None


def _build_mock_response(schedule_json: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "synthetic_schedule_json",
                                "arguments": json.dumps({"schedule_json": schedule_json}),
                            }
                        }
                    ]
                }
            }
        ]
    }


def _extract_failed_generation(exc: Exception) -> Optional[str]:
    payload: Any = None
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            try:
                content = getattr(response, "content", None)
                if isinstance(content, (bytes, bytearray)):
                    payload = json.loads(content.decode("utf-8"))
            except Exception:
                payload = None
    if payload is None:
        payload = getattr(exc, "body", None)
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = json.loads(payload.decode("utf-8"))
            except Exception:
                payload = None
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = None

    if isinstance(payload, dict):
        failed = payload.get("failed_generation")
        if failed:
            return failed
        error_block = payload.get("error")
        if isinstance(error_block, dict):
            failed = error_block.get("failed_generation")
            if failed:
                return failed
    return None


def _format_llm_error(exc: Exception) -> str:
    failed = _extract_failed_generation(exc)
    if failed:
        return f"{exc} | failed_generation: {failed}"
    return str(exc)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(relative: str) -> Path:
    return _project_root().joinpath(relative)


def _load_file_text(name: str) -> str:
    path = _resolve_project_path(name)
    if not path.exists():
        raise LLMServiceError(f"Missing required prompt file: {path}")
    return path.read_text(encoding="utf-8")


def _load_schema() -> Dict[str, Any]:
    schema_path = _resolve_project_path(SCHEMA_FILE)
    if not schema_path.exists():
        raise LLMServiceError(f"Missing schema file: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("schema", payload)


def _build_client(api_key: Optional[str], base_url: Optional[str]) -> OpenAI:
    key = api_key or _env_or_raise("OPENAI_API_KEY", "LLM API key is required")
    url = base_url or _env_or_default("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=key, base_url=url)


def _env_or_raise(name: str, message: str) -> str:
    import os

    value = os.environ.get(name)
    if not value:
        raise LLMServiceError(message)
    return value


def _env_or_default(name: str, default: str) -> str:
    import os

    return os.environ.get(name, default)


def _is_legacy_function_unsupported(exc: Exception) -> bool:
    message = str(getattr(exc, "message", "")) or str(exc)
    keywords = (
        "body.function_call",
        "body.functions",
        "function_call",
        "wrong_api_format",
        "unsupported",
    )
    return any(keyword in message for keyword in keywords)


def _invoke_function_or_tool(
    client: OpenAI,
    *,
    model: str,
    messages: List[Dict[str, Any]],
    function_name: str,
    description: str,
    parameters: Dict[str, Any],
) -> Any:
    function_def = {
        "name": function_name,
        "description": description,
        "parameters": parameters,
    }
    # Prefer modern tools/tool_choice first for compatibility
    try:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[{"type": "function", "function": function_def}],
            tool_choice={"type": "function", "function": {"name": function_name}},
        )
    except Exception as exc:
        logger.warning("Tool call failed for %s: %s", function_name, exc)
        if not _is_legacy_function_unsupported(exc):
            failed = _extract_schedule_from_failed_generation(_extract_failed_generation(exc))
            if failed is not None:
                logger.info("Using failed_generation payload for %s (tool call).", function_name)
                return _build_mock_response(failed)
            raise LLMServiceError(f"LLM tool call failed: {_format_llm_error(exc)}") from exc
    try:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            functions=[function_def],
            function_call={"name": function_name},
        )
    except Exception as exc:
        logger.error("Function call fallback also failed for %s: %s", function_name, exc)
        failed = _extract_schedule_from_failed_generation(_extract_failed_generation(exc))
        if failed is not None:
            logger.info("Using failed_generation payload for %s (function call).", function_name)
            return _build_mock_response(failed)
        raise LLMServiceError(f"LLM function call failed: {_format_llm_error(exc)}") from exc


def generate_schedule_json(
    user_message: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an initial schedule JSON using OpenAI function calling."""

    client = _build_client(api_key, base_url)
    system_prompt = _load_file_text(PROMPT_FILE)
    fjsp_schema = _load_schema()
    model_name = model or "gpt-4o"

    response = _invoke_function_or_tool(
        client,
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        function_name="generate_schedule_json",
        description="Generate initial FJSP schedule JSON from the provided user message (returned as schedule_json).",
        parameters={
            "type": "object",
            "properties": {"schedule_json": fjsp_schema},
            "required": ["schedule_json"],
        },
    )

    return _extract_schedule_json(response)


def update_schedule_json(
    current_json: Dict[str, Any],
    instruction: str,
    previous_messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing schedule JSON given user instructions."""

    client = _build_client(api_key, base_url)
    system_prompt = _load_file_text(PROMPT_UPDATE_FILE)
    fjsp_schema = _load_schema()
    model_name = model or "gpt-4o"

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if previous_messages:
        messages.extend(previous_messages)
    messages.extend(
        [
            {"role": "assistant", "content": "Current schedule JSON (do not modify directly):"},
            {"role": "assistant", "content": json.dumps(current_json)},
            {"role": "user", "content": instruction},
        ]
    )

    response = _invoke_function_or_tool(
        client,
        model=model_name,
        messages=messages,
        function_name="update_schedule_json",
        description="Return an updated FJSP schedule JSON (as schedule_json).",
        parameters={
            "type": "object",
            "properties": {"schedule_json": fjsp_schema},
            "required": ["schedule_json"],
        },
    )

    return _extract_schedule_json(response)


def update_solution_csv_llm(
    csv_path: str,
    instruction: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> pd.DataFrame:
    """Ask the LLM to apply local adjustments to an existing solution CSV."""

    model_name = model or "gpt-4o"
    client = _build_client(api_key, base_url)

    df = pd.read_csv(csv_path)
    prompt = (
        "You are an expert in Flexible Job Shop Scheduling (FJSP).\n"
        "Below is the current solution pool in CSV format. Each row represents an operation in a job, "
        "with columns: instance_id, job, operation, machine, start_time, end_time, duration.\n\n"
        f"User instruction: \"{instruction}\"\n\n"
        "Update the CSV minimally. Return ONLY the updated CSV with headers.\n\n"
        "Current CSV:\n"
        f"{df.to_csv(index=False)}"
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a scheduling assistant. Only output the updated CSV, no explanations."},
            {"role": "user", "content": prompt},
        ],
    )

    csv_text = response.choices[0].message.content
    if not csv_text:
        raise LLMServiceError("LLM returned empty CSV content")
    return pd.read_csv(io.StringIO(csv_text))


def decide_update_route(
    instruction: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    """Decide whether to update the schedule JSON or the solution CSV."""

    model_name = model or "gpt-4o"
    client = _build_client(api_key, base_url)

    decision_prompt = (
        "You are an expert in Flexible Job Shop Scheduling (FJSP).\n"
        f"Instruction:\n{instruction}\n\n"
        "Decide which update method:\n"
        "- Structural change -> update_schedule_json\n"
        "- Local adjustment  -> update_solution_csv_llm\n\n"
        "Reply ONLY with: update_schedule_json or update_solution_csv_llm"
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a scheduling assistant."},
            {"role": "user", "content": decision_prompt},
        ],
    )

    decision = (response.choices[0].message.content or "").strip()
    if decision not in {"update_schedule_json", "update_solution_csv_llm"}:
        raise LLMServiceError(f"Unexpected decision response: {decision}")
    return decision


def load_schedule_schema() -> Dict[str, Any]:
    """Expose the cached schedule schema for clients."""

    return _load_schema()


def _extract_schedule_json(response: Any) -> Dict[str, Any]:
    try:
        choice = response.choices[0]
        message = choice.message
    except Exception as exc:
        raise LLMServiceError(f"Malformed LLM response: {exc}") from exc

    args: Any = None
    function_call = getattr(message, "function_call", None)
    tool_calls = getattr(message, "tool_calls", None)

    if not function_call and isinstance(message, dict):
        function_call = message.get("function_call")
    if function_call and not isinstance(function_call, dict):
        function_call = {
            "name": getattr(function_call, "name", None),
            "arguments": getattr(function_call, "arguments", None),
        }

    if function_call:
        args = function_call.get("arguments")
    elif tool_calls:
        tool_call = tool_calls[0]
        if isinstance(tool_call, dict):
            fn = tool_call.get("function")
        else:
            fn = getattr(tool_call, "function", None)
        if fn:
            if not isinstance(fn, dict):
                fn = {
                    "name": getattr(fn, "name", None),
                    "arguments": getattr(fn, "arguments", None),
                }
            args = fn.get("arguments")
    elif isinstance(message, dict):
        args = message.get("content")

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f"Failed to decode LLM arguments: {exc}") from exc

    if isinstance(args, dict):
        payload = args.get("schedule_json") or args
    else:
        raise LLMServiceError("LLM response missing schedule_json")

    required_keys = {"J", "M", "instances"}
    if not required_keys.issubset(payload.keys()):
        raise LLMServiceError("schedule_json missing required keys J/M/instances")
    return payload
