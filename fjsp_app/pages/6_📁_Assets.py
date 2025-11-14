# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state

st.set_page_config(page_title="Assets", page_icon="📁", layout="wide")
init_session_state()

st.header("📁 Assets & History")
pool_dir = "solution_pools"
gantt_dir = "gantt_charts"

st.subheader("Solution Pools")
if os.path.isdir(pool_dir):
    files = sorted(os.listdir(pool_dir))
    if files:
        for f in files:
            st.write(f"- {f}")
    else:
        st.info("Empty.")
else:
    st.info("No solution_pools directory found.")

st.subheader("Gantt Charts")
if os.path.isdir(gantt_dir):
    imgs = [f for f in os.listdir(gantt_dir) if f.endswith(".png")]
    for g in sorted(imgs):
        st.image(os.path.join(gantt_dir, g), caption=g, use_container_width=True)
else:
    st.info("No gantt_charts directory found.")
