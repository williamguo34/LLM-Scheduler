from __future__ import annotations

import json
from difflib import unified_diff
from typing import Any, Dict, List

import pandas as pd

from fjsp_app.backend.transform import json_to_tables


def json_diff(current_json: Dict[str, Any], proposed_json: Dict[str, Any]) -> str:
    current_str = json.dumps(current_json, indent=2, sort_keys=True).splitlines()
    proposed_str = json.dumps(proposed_json, indent=2, sort_keys=True).splitlines()
    diff_lines = unified_diff(current_str, proposed_str, fromfile="current", tofile="proposed")
    return "\n".join(diff_lines)


def table_diff(current_json: Dict[str, Any], proposed_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    current_tables = json_to_tables(current_json)
    proposed_tables = json_to_tables(proposed_json)

    current_map = {job_id: (job_name, df.copy()) for job_id, job_name, df in current_tables}
    proposed_map = {job_id: (job_name, df.copy()) for job_id, job_name, df in proposed_tables}

    job_ids = sorted(set(current_map) | set(proposed_map))
    changes: List[Dict[str, Any]] = []

    for job_id in job_ids:
        current_entry = current_map.get(job_id)
        proposed_entry = proposed_map.get(job_id)
        current_df = current_entry[1] if current_entry else pd.DataFrame()
        proposed_df = proposed_entry[1] if proposed_entry else pd.DataFrame()

        # Align columns for comparison
        all_columns = list(dict.fromkeys(list(current_df.columns) + list(proposed_df.columns)))
        current_aligned = current_df.reindex(columns=all_columns).fillna("")
        proposed_aligned = proposed_df.reindex(columns=all_columns).fillna("")

        if current_aligned.equals(proposed_aligned):
            continue

        changes.append(
            {
                "job_id": job_id,
                "job_name": (proposed_entry or current_entry or (None,))[0],
                "current_rows": current_aligned.to_dict(orient="records"),
                "proposed_rows": proposed_aligned.to_dict(orient="records"),
            }
        )

    return changes
