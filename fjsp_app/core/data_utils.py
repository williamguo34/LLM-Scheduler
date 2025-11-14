import streamlit as st
import json, pandas as pd, os, sys
from importlib import import_module

# 确保能导入 backend (原 app_final 拆分后)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# 优先复用 backend 的实现
try:
    _backend = import_module("fjsp_app.backend")
    _json_to_tables = getattr(_backend, "json_to_tables", None)
    _tables_to_json = getattr(_backend, "tables_to_json", None)
except Exception:
    _backend = None
    _json_to_tables = _tables_to_json = None

def init_session_state():
    defaults = {
        "current_json": None,
        "tables": None,
        "messages": [],
        "conversation_stage": "initial",
        "pending_changes": None,
        "solve_results": None,
        "solution_pool": [],
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://models.inference.ai.azure.com",
        "MODEL_NAME": "gpt-4o"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def load_json_from_file(file):
    try:
        return json.load(file)
    except Exception as e:
        st.error(f"JSON load error: {e}")
        return None

def json_to_tables(data):
    if _json_to_tables:
        return _json_to_tables(data)
    tables = []
    for job in data.get("instances", []):
        df = pd.DataFrame(job.get("operations", []))
        tables.append((job["job_id"], job.get("job_n", f"Job {job['job_id']}"), df))
    return tables

def tables_to_json(tables, orig_json):
    if _tables_to_json:
        return _tables_to_json(tables, orig_json)
    instances = []
    for job_id, job_n, df in tables:
        ops = df.to_dict(orient="records")
        instances.append({"job_id": job_id, "job_n": job_n, "operations": ops})
    return {"J": orig_json["J"], "M": orig_json["M"], "instances": instances}

def normalize_re_for_display(df):
    out = df.copy()
    if "re" in out.columns:
        out["re"] = out["re"].astype(str).str.replace("|", " or ").str.replace("&", " and ", regex=False)
    return out

def denormalize_re_from_display(df):
    out = df.copy()
    if "re" in out.columns:
        out["re"] = out["re"].astype(str).str.replace(" or ", "|", regex=False).str.replace(" and ", "&", regex=False)
    return out

def ensure_chat_first_defaults():
    """初始化聊天优先体验所需的 Session 默认值。"""
    st.session_state.setdefault("ui_auto_apply", True)
    st.session_state.setdefault("ui_auto_solve", True)
    st.session_state.setdefault("ui_runs", 1)

def apply_pending_changes_if_needed():
    """在开启自动应用的情况下，应用待定提案并按需触发求解。"""
    pending = st.session_state.get("pending_changes")
    if not pending:
        return False
    if not st.session_state.get("ui_auto_apply", False):
        return False
    if not _backend:
        st.error("backend not importable.")
        return False

    st.session_state.current_json = pending
    try:
        st.session_state.tables = _backend.json_to_tables(st.session_state.current_json)
    except Exception:
        st.session_state.tables = None
    st.session_state.pending_changes = None
    st.session_state.messages.append({"role": "assistant", "content": "✅ Changes auto-applied."})

    if st.session_state.get("ui_auto_solve", False):
        try:
            from fjsp_app.core.ppo_solver import solve_with_runs

            solve_with_runs()
        except Exception as exc:
            st.warning(f"Auto-solve skipped: {exc}")
    return True
