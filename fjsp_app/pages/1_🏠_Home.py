# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state, load_json_from_file
from fjsp_app.core.validation_utils import quick_schema_summary

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")
init_session_state()

st.header("🏠 Home / Onboarding")
left, right = st.columns([2, 1])

with left:
    st.markdown("#### How to start")
    st.markdown("1) Import an existing schedule JSON **or** 2) Go to **Problem Builder** to describe your problem.")
    st.page_link("pages/2_🧩_Problem_Builder.py", label="Open Problem Builder", icon="🧩")

    st.markdown("#### Import schedule JSON")
    up = st.file_uploader("Upload a `schedule.json`", type=["json"])
    if up:
        data = load_json_from_file(up)
        if data:
            st.session_state.current_json = data
            st.session_state.tables = None
            st.success("✅ JSON loaded. Go to Table Editor or Builder.")
            st.page_link("pages/3_🧾_Table_Editor.py", label="Open Table Editor", icon="🧾")

with right:
    st.markdown("#### Current Session")
    if st.session_state.current_json:
        J, M, ops = quick_schema_summary(st.session_state.current_json)
        st.metric("Jobs", J)
        st.metric("Machines", M)
        st.metric("Operations", ops)
    else:
        st.info("No active schedule loaded.")
