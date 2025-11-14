import json, difflib, pandas as pd, streamlit as st
from .transform import json_to_tables

def show_json_diff(old_json,new_json):
    old_str=json.dumps(old_json,indent=2).splitlines(); new_str=json.dumps(new_json,indent=2).splitlines()
    diff='\n'.join(difflib.unified_diff(old_str,new_str,fromfile='Current',tofile='Proposed'))
    if diff: st.code(diff, language='diff')
    else: st.info('No changes detected')

def show_table_comparison(old_json, new_json):
    old_tables=json_to_tables(old_json); new_tables=json_to_tables(new_json)
    old_map={jid:(jn,df) for jid,jn,df in old_tables}; new_map={jid:(jn,df) for jid,jn,df in new_tables}
    for jid in sorted(set(old_map)|set(new_map)):
        old_job=old_map.get(jid); new_job=new_map.get(jid)
        job_n=(new_job or old_job)[0]
        old_df=old_job[1].copy() if old_job else pd.DataFrame(); new_df=new_job[1].copy() if new_job else pd.DataFrame()
        # Align columns/rows positionally
        all_cols=list(dict.fromkeys(list(old_df.columns)+list(new_df.columns)))
        max_rows=max(len(old_df),len(new_df))
        old_df=old_df.reindex(range(max_rows)).reset_index(drop=True).reindex(columns=all_cols)
        new_df=new_df.reindex(range(max_rows)).reset_index(drop=True).reindex(columns=all_cols)
        def is_na(v):
            if v is None: return True
            if isinstance(v,(list,tuple)): return len(v)==0
            try:
                import numpy as _np
                if isinstance(v,_np.ndarray): return v.size==0
            except: pass
            try: return pd.isna(v)
            except: return False
        changed=[]
        for i in range(max_rows):
            row_changed=False
            for col in all_cols:
                ov=old_df.at[i,col] if i < len(old_df) else None
                nv=new_df.at[i,col] if i < len(new_df) else None
                if is_na(ov) and is_na(nv): continue
                if is_na(ov)!=is_na(nv) or str(ov)!=str(nv): row_changed=True; break
            changed.append(row_changed)
        idx_changed=[i for i,v in enumerate(changed) if v]
        if not idx_changed: continue
        st.markdown(f'### Job {jid}: {job_n}')
        col_old, col_new = st.columns(2)
        def style_func(base_df, other_df, color):
            def apply_row(r):
                styles=[]
                for c in base_df.columns:
                    try: oth=other_df.at[r.name,c]
                    except: oth=None
                    v=r[c]
                    if (pd.isna(v) and not pd.isna(oth)) or (not pd.isna(v) and pd.isna(oth)) or (str(v)!=str(oth)):
                        styles.append(f'background-color: {color}')
                    else: styles.append('')
                return styles
            return apply_row
        old_changed=old_df.loc[idx_changed].reset_index(drop=True); new_changed=new_df.loc[idx_changed].reset_index(drop=True)
        with col_old:
            st.markdown('**Current (changed rows)**')
            st.dataframe(old_changed.style.apply(style_func(old_changed,new_changed,'#ffcdd2'), axis=1), use_container_width=True)
        with col_new:
            st.markdown('**Proposed (changed rows)**')
            st.dataframe(new_changed.style.apply(style_func(new_changed,old_changed,'#c8e6c9'), axis=1), use_container_width=True)
