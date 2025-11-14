import streamlit as st
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

try:
    import fjsp_app.backend as _backend
except Exception:
    _backend = None

def validate_schedule_for_ppo(schedule_json):
    if _backend and hasattr(_backend, "validate_schedule_for_ppo"):
        return _backend.validate_schedule_for_ppo(schedule_json)
    # 兜底最小校验
    if not schedule_json:
        return False, "Empty schedule"
    if not all(k in schedule_json for k in ["J", "M", "instances"]):
        return False, "Missing keys J/M/instances"
    if not schedule_json.get("instances"):
        return False, "No instances"
    return True, None

def quick_schema_summary(schedule_json):
    J = schedule_json.get("J", 0)
    M = schedule_json.get("M", 0)
    ops = sum(len(job.get("operations", [])) for job in schedule_json.get("instances", []))
    return J, M, ops

def check_deadlines(deadlines_list):
    if _backend and hasattr(_backend, "check_deadlines"):
        return _backend.check_deadlines(deadlines_list)
    st.info("Prototype: deadlines checker not wired.")
    return None

def check_precedence_constraints():
    if _backend and hasattr(_backend, "check_precedence_constraints"):
        return _backend.check_precedence_constraints()
    st.info("Prototype: precedence checker not wired.")
    return None
