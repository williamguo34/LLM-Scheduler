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


def solve_with_runs():
    """Trigger a solve cycle using backend's PPO routine (legacy app_final extracted)."""
    if not _backend or not hasattr(_backend, "solve_with_ppo"):
        st.error("solve_with_ppo() not available.")
        return

    if hasattr(_backend, "load_validation_model"):
        weights_key = st.session_state.get("MODEL_WEIGHTS_DIR", "")
        try:
            _backend.load_validation_model(cache_key=str(weights_key))
        except TypeError:
            try:
                _backend.load_validation_model()
            except Exception:
                pass
        except Exception:
            pass

    _backend.solve_with_ppo()


def show_results_if_any():
    """Render results and gantt charts if available in session state."""
    if not _backend or not hasattr(_backend, "display_results"):
        return
    results = st.session_state.get("solve_results")
    if results:
        _backend.display_results(results)


# Backwards-compatible helpers --------------------------------------------
def solve_with_ppo(*_, **__):
    solve_with_runs()


def display_results(results_list):
    if not _backend or not hasattr(_backend, "display_results"):
        st.error("display_results() not available.")
        return
    _backend.display_results(results_list)
