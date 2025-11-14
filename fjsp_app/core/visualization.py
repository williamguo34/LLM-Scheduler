import streamlit as st
import json, difflib, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

try:
    import fjsp_app.backend as _backend
except Exception:
    _backend = None

def show_table_comparison(old_json, new_json):
    """Use backend's table comparison (legacy app_final deprecated)."""
    if new_json is None:
        st.warning("No proposed changes to show.")
        return

    base = old_json if isinstance(old_json, dict) and "instances" in old_json else {"J": 0, "M": 0, "instances": []}

    use_app_fn = _backend and hasattr(_backend, "show_table_comparison")
    if use_app_fn:
        try:
            return _backend.show_table_comparison(base, new_json)
        except Exception as e:
            st.warning(f"Table comparison failed ({e}); falling back to text diff.")
    else:
        st.warning("show_table_comparison not available; falling back to text diff.")

    show_diff_view(base, new_json)

def show_diff_view(old_json, new_json):
    """文本 unified diff 兜底"""
    try:
        old_str = json.dumps(old_json, indent=2).splitlines() if old_json else []
        new_str = json.dumps(new_json, indent=2).splitlines() if new_json else []
        diff = difflib.unified_diff(old_str, new_str, fromfile='Current', tofile='Proposed')
        st.code("\n".join(diff), language="diff")
    except Exception as e:
        st.error(f"Diff render error: {e}")
