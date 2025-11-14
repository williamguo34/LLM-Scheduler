import numpy as np, pandas as pd, streamlit as st

def openai_json_to_npy(data):
    try:
        n_jobs = data['J']; n_machines = data['M']; num_instances = 1
        max_dim = max(n_jobs, n_machines)
        arr = np.full((num_instances, n_jobs, max_dim, max_dim), -40)
        for job in data['instances']:
            job_id = job['job_id']-1
            if job_id >= n_jobs: continue
            for op_idx, op in enumerate(job['operations']):
                if op_idx >= max_dim: continue
                re_field = op['re']
                if '|' in re_field:
                    for option in re_field.split('|'):
                        if ':' in option:
                            m_str,t_str = option.split(':')
                            try:
                                m = int(m_str.strip())-1; t = float(t_str.strip())
                                if 0<=m<max_dim: arr[0,job_id,op_idx,m]=t
                            except: pass
                elif '&' in re_field and ':' in re_field:
                    machines_part,time_part = re_field.split(':',1)
                    try:
                        t = float(time_part.strip())
                        for i,m_s in enumerate(machines_part.split('&')):
                            try:
                                m = int(m_s.strip())-1
                                if 0<=m<max_dim:
                                    arr[0,job_id,min(op_idx+i,max_dim-1),m]=t
                            except: pass
                    except: pass
                elif ':' in re_field:
                    m_str,t_str = re_field.split(':',1)
                    try:
                        m = int(m_str.strip())-1; t = float(t_str.strip())
                        if 0<=m<max_dim: arr[0,job_id,op_idx,m]=t
                    except: pass
        return arr
    except Exception as e:
        st.error(f'openai_json_to_npy error: {e}')
        return None

def split_re(re_str):
    if '|' in re_str:
        resources=[]; times=[]
        for p in re_str.split('|'):
            if ':' in p:
                r,t=p.split(':'); resources.append(r); times.append(t)
        return '|'.join(resources),'|'.join(times)
    if ':' in re_str:
        r,t = re_str.split(':'); return r,t
    return re_str,''

def combine_re(resources,times):
    if '|' in resources:
        res_list=resources.split('|'); time_list=times.split('|')
        return '|'.join(f'{r}:{t}' for r,t in zip(res_list,time_list))
    if resources and times:
        return f'{resources}:{times}'
    return resources

def json_to_tables(data):
    tables=[]
    for job in data['instances']:
        for op in job['operations']:
            res,t = split_re(op['re']); op['resource']=res; op['time']=t
        df = pd.DataFrame(job['operations']).drop(columns=['re'])
        tables.append((job['job_id'], job.get('job_n'), df))
    return tables

def tables_to_json(tables, orig_json):
    instances=[]
    for job_id,job_n,df in tables:
        ops=df.copy(); ops['re']=ops.apply(lambda r: combine_re(str(r['resource']), str(r['time'])), axis=1)
        ops=ops.drop(columns=['resource','time']).to_dict(orient='records')
        instances.append({'job_id':job_id,'job_n':job_n,'operations':ops})
    return {'J':orig_json['J'],'M':orig_json['M'],'instances':instances}
