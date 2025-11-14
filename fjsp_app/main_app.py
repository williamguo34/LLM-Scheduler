# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state

st.set_page_config(page_title="FJSP Scheduling Assistant", page_icon="🤖", layout="wide")
init_session_state()

st.title("🤖 FJSP Scheduling Assistant")
st.markdown("*Describe → Generate/Update → Review → Solve → Visualize*")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🧭 Start")
    st.page_link("pages/1_🏠_Home.py", label="Home / Onboarding", icon="🏠")
with col2:
    st.markdown("### 🧩 Build")
    st.page_link("pages/2_🧩_Problem_Builder.py", label="Problem Builder", icon="🧩")
with col3:
    st.markdown("### ⚙️ Solve")
    st.page_link("pages/4_⚙️_Solver_Hub.py", label="Solver Hub", icon="⚙️")

st.divider()
st.info("Use the left sidebar or the quick links above to navigate.")
