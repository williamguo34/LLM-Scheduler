import streamlit as st
import os, sys
from importlib import import_module

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

try:
    _backend = import_module("fjsp_app.backend")
except Exception as e:
    _backend = None
    st.error(f"Cannot import backend: {e}")

def _inject_settings():
    """Legacy no-op: backend directly reads credentials from session_state/env."""
    if not _backend:
        return
    # backend uses session_state/env directly

def decide_update_route(user_instruction: str) -> str:
    # 1) 如果还没有任何 problem JSON，必然是首次描述 -> 必须生成 schedule
    if st.session_state.get("current_json") is None:
        return "update_schedule_json"

    # 2) 如果 backend 决策接口不可用，安全回退到 schedule json 更新
    if not _backend or not hasattr(_backend, "get_llm_update_decision"):
        return "update_schedule_json"

    _inject_settings()
    model = st.session_state.get("MODEL_NAME") or "gpt-4o"
    try:
        decision = _backend.get_llm_update_decision(user_instruction, model=model).strip()
    except Exception as exc:
        st.error(f"Decision error: {exc}")
        return "update_schedule_json"

    if decision not in ("update_schedule_json", "update_solution_csv_llm"):
        return "update_schedule_json"

    # 3) 若判为 CSV 级别微调，但当前还没有任何 solution pool CSV（即还没有求解过），则强制回退为 schedule 更新
    if decision == "update_solution_csv_llm":
        if not _latest_solution_pool_csv():
            # 给出提示，仅一次性信息
            st.info("(回退) 尚未产生 solution pool，改为对 schedule JSON 进行更新。请先求解再做 CSV 局部微调。")
            return "update_schedule_json"

    return decision


def run_generate_schedule_json(user_message: str):
    if not _backend or not hasattr(_backend, "generate_schedule_json"):
        st.error("generate_schedule_json() not available.")
        return None
    _inject_settings()
    try:
        return _backend.generate_schedule_json(user_message)
    except Exception as exc:
        st.error(f"Generate failed: {exc}")
        return None


def run_update_schedule_json(current_json, instruction, prev_messages=None):
    if not _backend or not hasattr(_backend, "update_schedule_json"):
        st.error("update_schedule_json() not available.")
        return None
    _inject_settings()
    try:
        return _backend.update_schedule_json(current_json, instruction, prev_messages=prev_messages)
    except Exception as exc:
        st.error(f"Update failed: {exc}")
        return None


class SimpleNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _latest_solution_pool_csv():
    pool = st.session_state.get("solution_pool") or []
    for sol in reversed(pool):
        path = sol.get("pool_csv") if isinstance(sol, dict) else None
        if path and os.path.exists(path):
            return path
    return None


def run_update_solution_csv_llm(user_instruction: str):
    if not _backend or not hasattr(_backend, "update_solution_csv_llm"):
        return SimpleNamespace(success=False, message="update_solution_csv_llm() not available.")
    _inject_settings()
    csv_path = _latest_solution_pool_csv()
    if not csv_path:
        # 主动引导：返回一个 fallback 提示
        return SimpleNamespace(
            success=False,
            message=(
                "❌ No solution pool CSV found (还没有求解结果). \n"
                "➡️ 请先执行一次求解 (Solve / PPO) 生成 solution_pool 后再尝试局部 CSV 微调，"
                "或直接用自然语言继续修改问题结构。"
            )
        )
    try:
        model = st.session_state.get("MODEL_NAME") or "gpt-4o"
        updated_df = _backend.update_solution_csv_llm(csv_path, user_instruction, model=model)
        updated_csv = csv_path.replace(".csv", "_llm_updated.csv")
        updated_df.to_csv(updated_csv, index=False)
        return SimpleNamespace(success=True, message=f"✅ CSV updated by LLM: {updated_csv}")
    except Exception as exc:
        return SimpleNamespace(success=False, message=f"❌ CSV update failed: {exc}")


def create_or_update_from_message(user_msg: str):
    route = decide_update_route(user_msg)
    if route == "update_schedule_json":
        if st.session_state.get("current_json") is None:
            proposed = run_generate_schedule_json(user_msg)
        else:
            proposed = run_update_schedule_json(
                st.session_state.current_json,
                user_msg,
                st.session_state.get("messages"),
            )
        if proposed:
            st.session_state.pending_changes = proposed
            return True, "📝 Proposed changes prepared."
        return False, "❌ Failed to produce a schedule proposal."

    if route == "update_solution_csv_llm":
        result = run_update_solution_csv_llm(user_msg)
        return result.success, result.message

    return False, f"❌ Unknown decision route: {route}"
