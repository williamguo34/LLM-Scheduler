import numpy as np, streamlit as st

def validate_schedule_for_ppo(schedule_json):
    problems=[]
    try:
        instances=schedule_json.get('instances',[])
        if not instances: return False,'No job instances found'
        for job in instances:
            jid=job.get('job_id'); ops=job.get('operations',[])
            if not isinstance(ops,list) or not ops:
                problems.append(f'Job {jid}: no operations'); continue
            for op in ops:
                re_field=op.get('re',''); op_id=op.get('op_id')
                if not isinstance(re_field,str) or ':' not in re_field:
                    problems.append(f'Job {jid} Op {op_id}: invalid re'); continue
                choices=re_field.split('|') if '|' in re_field else [re_field]
                valid=False
                for choice in choices:
                    if ':' not in choice: continue
                    machines_part,time_part=choice.split(':',1)
                    mids=machines_part.split('&')
                    try:
                        _=[int(m.strip()) for m in mids if m.strip()]
                        _t=float(time_part.strip()); valid=True; break
                    except: continue
                if not valid:
                    problems.append(f'Job {jid} Op {op_id}: no valid machine:time pair in {re_field}')
        if problems: return False,'; '.join(problems)
        return True,None
    except Exception as e:
        return False,f'Validation exception: {e}'

def check_deadlines(deadlines_list):
    if not getattr(streamlit:=__import__('streamlit').session_state,'solution_pool',None):
        st.error('No solution pool available'); return None
    try:
        deadlines=np.array(deadlines_list); np.save('deadlines_temp.npy',deadlines)
        pool_data=[]
        for sol in st.session_state.solution_pool:
            pool_data.append({'instance_id':sol['instance_id'],'job':0,'operation':0,'machine':0,'start_time':0,'end_time':sol['makespan'],'makespan':sol['makespan']})
        import pandas as pd
        df=pd.DataFrame(pool_data); df.to_csv('solution_pool_temp.csv',index=False)
        st.info('✅ Deadlines + pool saved')
        return {'deadlines_path':'deadlines_temp.npy','pool_path':'solution_pool_temp.csv','valid_solutions':len(st.session_state.solution_pool)}
    except Exception as e:
        st.error(f'Deadline check error: {e}'); return None

def extract_precedence_matrix(json_data):
    try:
        n_jobs=json_data['J']; matrix=np.zeros((n_jobs,n_jobs),dtype=int)
        for job in json_data['instances']:
            job_id=job['job_id']-1
            for op in job['operations']:
                if 'pre' in op and op['pre']:
                    for pre_op_id in op['pre']:
                        for check_job in json_data['instances']:
                            for check_op in check_job['operations']:
                                if check_op['op_id']==pre_op_id:
                                    pre_job_id=check_job['job_id']-1
                                    if pre_job_id!=job_id: matrix[pre_job_id, job_id]=1
        return matrix if np.any(matrix) else None
    except Exception as e:
        st.error(f'precedence extraction error: {e}'); return None

def check_precedence_constraints():
    if not getattr(st.session_state,'solution_pool',None):
        st.error('No solution pool available'); return None
    matrix = extract_precedence_matrix(st.session_state.current_json)
    if matrix is not None:
        np.save('precedence_matrix_temp.npy', matrix)
        st.info('✅ Precedence matrix extracted')
        return {'precedence_path':'precedence_matrix_temp.npy','precedence_matrix':matrix}
    else:
        st.warning('No precedence constraints found')
        return None
