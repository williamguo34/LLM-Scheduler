# --- path bootstrap: add project root (~/Yuchu) ---
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

import streamlit as st
from fjsp_app.core.data_utils import init_session_state, json_to_tables, tables_to_json, normalize_re_for_display, denormalize_re_from_display
from fjsp_app.core.validation_utils import validate_schedule_for_ppo, quick_schema_summary

st.set_page_config(page_title="Table Editor", page_icon="🧾", layout="wide")
init_session_state()

st.header("🧾 Table Editor")
if not st.session_state.current_json:
    st.warning("No schedule loaded. Go to Home or Problem Builder.")
    st.stop()

J, M, ops = quick_schema_summary(st.session_state.current_json)
st.caption(f"Jobs: {J} | Machines: {M} | Ops: {ops}")

tables = json_to_tables(st.session_state.current_json)
num_jobs = len(tables)
num_cols = min(3, num_jobs)
page = st.number_input("Page", min_value=0, max_value=max(0, (num_jobs-1)//num_cols), value=0) if num_jobs > num_cols else 0
start, end = page * num_cols, min(page * num_cols + num_cols, num_jobs)
cols = st.columns(end - start)

edited_partial = []
for col, (job_id, job_n, df) in zip(cols, tables[start:end]):
    with col:
        st.markdown(f"**Job {job_id}: {job_n}**")
        df_disp = normalize_re_for_display(df)
        edited_df = st.data_editor(df_disp, num_rows="dynamic", key=f"editor_{job_id}")
        edited_df = denormalize_re_from_display(edited_df)
        edited_df["job_id"] = job_id
        edited_df["job_n"] = job_n
        edited_partial.append((job_id, job_n, edited_df))

if st.button("Save Manual Edits", type="primary"):
    full_map = {jid: (jn, dfx) for jid, jn, dfx in tables}
    for jid, jn, edf in edited_partial:
        full_map[jid] = (jn, edf)
    merged = [(jid, full_map[jid][0], full_map[jid][1]) for jid, _, _ in tables]
    new_json = tables_to_json(merged, st.session_state.current_json)
    ok, msg = validate_schedule_for_ppo(new_json)
    if not ok:
        st.error(f"Validation failed: {msg}")
    else:
        st.session_state.current_json = new_json
        st.success("Manual edits saved.")
        st.rerun()
