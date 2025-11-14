# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state
from fjsp_app.core.validation_utils import check_deadlines, check_precedence_constraints

st.set_page_config(page_title="Constraints", page_icon="📊", layout="wide")
init_session_state()

st.header("📊 Constraints & Reports")
if not st.session_state.current_json:
    st.warning("No schedule loaded.")
    st.stop()

tab1, tab2 = st.tabs(["Deadlines", "Precedence"])
with tab1:
    st.markdown("#### Deadlines")
    user_list = st.text_area("Enter deadlines as comma-separated numbers (demo)", value="100, 120, 150")
    if st.button("Check Deadlines"):
        try:
            deadlines = [float(x.strip()) for x in user_list.split(",") if x.strip()]
            res = check_deadlines(deadlines)
            if res:
                st.success("Saved for checking.")
                st.write(res)
        except Exception as e:
            st.error(str(e))

with tab2:
    st.markdown("#### Precedence")
    if st.button("Extract Precedence Matrix"):
        res = check_precedence_constraints()
        if res:
            st.success("Precedence extracted.")
            mat = res.get("precedence_matrix", None)
            st.write("Matrix shape:", getattr(mat, "shape", None) if mat is not None else None)
