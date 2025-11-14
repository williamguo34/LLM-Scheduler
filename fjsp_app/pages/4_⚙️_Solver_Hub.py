# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state
from fjsp_app.core.ppo_solver import solve_with_ppo, display_results
from fjsp_app.backend.solver import solve_with_iaoa_gns

st.set_page_config(page_title="Solver Hub", page_icon="⚙️", layout="wide")
init_session_state()

st.header("⚙️ Solver Hub")
if not st.session_state.current_json:
    st.warning("No schedule loaded. Go to Home or Problem Builder.")
    st.stop()

left, right = st.columns([1, 2])
with left:
    st.subheader("Run")
    
    # Algorithm selection
    algorithm = st.radio(
        "Select Algorithm",
        ["PPO", "IAOA+GNS"],
        help="PPO: Reinforcement Learning approach\nIAOA+GNS: Metaheuristic with Grade Neighborhood Search"
    )
    
    # Algorithm-specific parameters
    if algorithm == "IAOA+GNS":
        st.subheader("IAOA+GNS Parameters")
        pop_size = st.slider("Population Size", 10, 100, 30, help="Number of solutions in population")
        max_iterations = st.slider("Max Iterations", 10, 100, 50, help="Maximum optimization iterations")
        num_runs = st.slider("Number of Runs", 1, 5, 1, help="Number of independent runs")
        
        st.session_state.iaoa_pop_size = pop_size
        st.session_state.iaoa_max_iterations = max_iterations
        st.session_state.iaoa_num_runs = num_runs
    
    # Solve button
    if algorithm == "PPO":
        if st.button("🚀 Solve with PPO", type="primary"):
            solve_with_ppo()
    else:
        if st.button("🚀 Solve with IAOA+GNS", type="primary"):
            solve_with_iaoa_gns()

with right:
    st.subheader("Results")
    if st.session_state.solve_results:
        display_results(st.session_state.solve_results)
    else:
        st.info(f"No results yet. Click **Solve with {algorithm}**.")
