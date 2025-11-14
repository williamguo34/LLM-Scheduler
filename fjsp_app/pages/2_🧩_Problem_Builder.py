"""Problem Builder Page

Unified version avoiding duplicate set_page_config calls. Provides:
- Current schedule overview
- Chat-first iterative problem construction
- Auto-apply + auto-solve controls (sidebar)
"""

# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import (
    init_session_state,
    ensure_chat_first_defaults,
    apply_pending_changes_if_needed,
)
from fjsp_app.core.llm_interface import create_or_update_from_message
from fjsp_app.core.validation_utils import quick_schema_summary
from fjsp_app.core.visualization import show_table_comparison
from fjsp_app.core.ppo_solver import solve_with_runs, show_results_if_any
from fjsp_app.backend import json_to_tables as backend_json_to_tables

st.set_page_config(page_title="Problem Builder", page_icon="🧩", layout="wide")
init_session_state()
ensure_chat_first_defaults()

# Auto-apply pending changes early if needed
if st.session_state.get("pending_changes") and st.session_state.get("ui_auto_apply", False):
    if apply_pending_changes_if_needed():
        st.rerun()

st.title("🧩 Problem Builder")

with st.sidebar:
    st.markdown("**Chat Settings**")
    st.session_state.ui_auto_apply = st.checkbox(
        "Auto-apply proposed changes", value=st.session_state.ui_auto_apply
    )
    st.session_state.ui_auto_solve = st.checkbox(
        "Auto-solve after apply", value=st.session_state.ui_auto_solve
    )
    st.number_input(
        "Solve runs (fixed to 1 current)",
        min_value=1,
        max_value=10,
        value=st.session_state.ui_runs,
        step=1,
        key="ui_runs",
    )
    st.text_input(
        "MODEL_WEIGHTS_DIR",
        key="MODEL_WEIGHTS_DIR",
        value=st.session_state.get("MODEL_WEIGHTS_DIR", "saved_network/FJSP_J10M10/best_value000"),
    )
    st.text_input(
        "OPENAI_API_KEY",
        key="OPENAI_API_KEY",
        value=st.session_state.get("OPENAI_API_KEY", ""),
        type="password",
        help="Your OpenAI-compatible API key. Stored only in this Streamlit session (not written to disk).",
    )
    st.text_input(
        "OPENAI_BASE_URL",
        key="OPENAI_BASE_URL",
        value=st.session_state.get("OPENAI_BASE_URL", "https://models.inference.ai.azure.com"),
        help="Override base URL if using a custom gateway (optional).",
    )

with st.expander("📦 Current Schedule Overview", expanded=False):
    if st.session_state.current_json:
        J, M, ops = quick_schema_summary(st.session_state.current_json)
        st.write(f"- **Jobs**: {J} | **Machines**: {M} | **Operations**: {ops}")
    else:
        st.info("No schedule yet. Start by describing it in the chat below.")

st.subheader("💬 Conversation")
for msg in st.session_state.get("messages", []):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_msg = st.chat_input("Describe or modify your scheduling problem…")
if user_msg:
    st.session_state.messages.append({"role": "user", "content": user_msg})
    ok, info = create_or_update_from_message(user_msg)
    st.session_state.messages.append({"role": "assistant", "content": info})
    if apply_pending_changes_if_needed():
        st.rerun()

if st.session_state.get("pending_changes"):
    st.divider()
    st.subheader("📋 Proposed Changes")
    show_table_comparison(
        st.session_state.get("current_json"), st.session_state.get("pending_changes")
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Accept Changes", type="primary", use_container_width=True):
            new = st.session_state.get("pending_changes")
            st.session_state.current_json = new
            try:
                st.session_state.tables = backend_json_to_tables(st.session_state.current_json)
            except Exception:
                st.session_state.tables = None
            st.session_state.pending_changes = None
            st.session_state.messages.append(
                {"role": "assistant", "content": "✅ Changes applied."}
            )
            if st.session_state.get("ui_auto_solve", False):
                solve_with_runs()
            st.rerun()
    with col2:
        if st.button("❌ Reject Changes", use_container_width=True):
            st.session_state.pending_changes = None
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Changes rejected."}
            )
            st.rerun()

st.divider()
st.subheader("📊 Results")
show_results_if_any()

if st.session_state.get("current_json") and not st.session_state.get("solve_results"):
    if st.button("🚀 Solve now", type="primary"):
        solve_with_runs()
        st.rerun()
