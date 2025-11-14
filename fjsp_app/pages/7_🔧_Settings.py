# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state

st.set_page_config(page_title="Settings", page_icon="🔧", layout="wide")
init_session_state()

st.header("🔧 Settings")
st.markdown("#### OpenAI")
st.text_input("OPENAI_API_KEY", key="OPENAI_API_KEY", type="password")
st.text_input("OPENAI_BASE_URL", key="OPENAI_BASE_URL")
st.text_input("MODEL_NAME", key="MODEL_NAME")
st.text_input(
	"MODEL_WEIGHTS_DIR",
	key="MODEL_WEIGHTS_DIR",
	value=st.session_state.get("MODEL_WEIGHTS_DIR", "saved_network/FJSP_J10M10/best_value000"),
)

st.caption("Backend reads these values directly; legacy monolithic file removed.")
