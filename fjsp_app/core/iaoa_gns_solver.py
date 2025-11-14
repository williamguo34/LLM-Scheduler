"""
IAOA+GNS Solver wrapper for Yuchu fjsp_app.
Similar structure to PPO solver for consistency.
"""

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


def solve_with_iaoa_gns():
    """Trigger a solve cycle using IAOA+GNS algorithm."""
    if not _backend or not hasattr(_backend, "solve_with_iaoa_gns"):
        st.error("solve_with_iaoa_gns() not available.")
        return
    
    _backend.solve_with_iaoa_gns()


def show_results_if_any():
    """Render results and gantt charts if available in session state."""
    if not _backend or not hasattr(_backend, "display_results"):
        return
    results = st.session_state.get("solve_results")
    if results:
        _backend.display_results(results)

