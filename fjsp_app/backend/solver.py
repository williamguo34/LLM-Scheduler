import time, os, shutil, numpy as np, pandas as pd, streamlit as st, torch
from Params import configs
from PPOwithValue import PPO
from .transform import openai_json_to_npy
from .validation import validate_schedule_for_ppo
from .transform import json_to_tables
from validation_csv import validate, enrich_solution_csv, generate_gantt_from_df

# IAOA+GNS imports - using relative import from parent package
from ..core.problem_adapter import yuchu_json_to_problem_instance, solution_to_yuchu_format
from ..core.iaoa_gns import IAOAGNSAlgorithm, IAOAConfig

def prepare_data_for_validation(npy_data):
    import numpy as _np, torch as _torch
    if not isinstance(npy_data,_np.ndarray): npy_data=_np.array(npy_data)
    if len(npy_data.shape)==3: npy_data=npy_data.reshape(1,*npy_data.shape)
    return _torch.FloatTensor(npy_data)

@st.cache_resource
def load_validation_model():
    try:
        ppo = PPO(configs.lr, configs.gamma, configs.k_epochs, configs.eps_clip,
                  n_j=10,n_m=10,num_layers=configs.num_layers,neighbor_pooling_type=configs.neighbor_pooling_type,
                  input_dim=configs.input_dim,hidden_dim=configs.hidden_dim,
                  num_mlp_layers_feature_extract=configs.num_mlp_layers_feature_extract,
                  num_mlp_layers_actor=configs.num_mlp_layers_actor,hidden_dim_actor=configs.hidden_dim_actor,
                  num_mlp_layers_critic=configs.num_mlp_layers_critic,hidden_dim_critic=configs.hidden_dim_critic)
        filepath='saved_network/FJSP_J10M10/best_value000'
        job_path=os.path.join(filepath,'policy_job.pth'); mch_path=os.path.join(filepath,'policy_mch.pth')
        if torch.cuda.is_available():
            ppo.policy_job.load_state_dict(torch.load(job_path, weights_only=True))
            ppo.policy_mch.load_state_dict(torch.load(mch_path, weights_only=True))
        else:
            ppo.policy_job.load_state_dict(torch.load(job_path,map_location=torch.device('cpu'), weights_only=True))
            ppo.policy_mch.load_state_dict(torch.load(mch_path,map_location=torch.device('cpu'), weights_only=True))
        return ppo
    except Exception as e:
        st.error(f'Model load error: {e}')
        return None

def save_solution_pool(solution_pool, current_json):
    from .transform import openai_json_to_npy as _to_npy
    try:
        os.makedirs('solution_pools', exist_ok=True)
        ts=time.strftime('%Y%m%d_%H%M%S')
        pool_df=pd.DataFrame(solution_pool)
        pool_csv_path=f'solution_pools/instance_{ts}.csv'
        pool_df.to_csv(pool_csv_path, index=False)
        instance_json_path=f'solution_pools/instance_{ts}.json'
        import json
        with open(instance_json_path,'w') as f: json.dump(current_json,f,indent=2)
        npy=_to_npy(current_json); instance_npy_path=None
        if npy is not None:
            instance_npy_path=f'solution_pools/instance_{ts}.npy'
            np.save(instance_npy_path,npy)
        return {'pool_csv':pool_csv_path,'instance_json':instance_json_path,'instance_npy':instance_npy_path,'timestamp':ts}
    except Exception as e:
        st.error(f'save_solution_pool error: {e}')
        return None

def solve_with_ppo():
    with st.spinner('Running PPO scheduling algorithm...'):
        try:
            valid,msg = validate_schedule_for_ppo(st.session_state.current_json)
            if not valid:
                st.error(f'Validation failed: {msg}'); return
            npy_data=openai_json_to_npy(st.session_state.current_json)
            if npy_data is None: st.error('NPY conversion failed'); return
            ppo=load_validation_model()
            if ppo is None: st.error('Model load failed'); return
            tensor=prepare_data_for_validation(npy_data)
            if tensor is None: st.error('Tensor prep failed'); return
            num_runs=1; results_list=[]; solution_pool=[]
            progress=st.progress(0); status=st.empty()
            for run in range(num_runs):
                status.text(f'Running scheduling... ({run+1}/{num_runs})')
                progress.progress((run+1)/num_runs)
                results=validate([tensor],1,ppo.policy_job, ppo.policy_mch, run_number=run+1)
                if results and len(results)>0:
                    makespan=float(results[0]); results_list.append(makespan)
                    os.makedirs('solution_pools', exist_ok=True)
                    ts=time.strftime('%Y%m%d_%H%M%S'); src='solution_pool.csv'; saved=None; rows=0
                    if os.path.exists(src):
                        saved=f'solution_pools/solution_pool_{ts}_run{run+1}.csv'
                        try:
                            shutil.move(src,saved)
                            try:
                                dfp=pd.read_csv(saved); rows=len(dfp)
                            except: rows=0
                        except Exception as e:
                            st.warning(f'Move solution_pool.csv failed: {e}')
                    solution_pool.append({'instance_id':run+1,'makespan':makespan,'run_number':run+1,'gantt_file':f'run_{run+1}_gantt_chart_instance_1.png','pool_csv':saved,'pool_rows':int(rows)})
                else:
                    st.warning(f'Run {run+1} produced no result')
            if results_list:
                st.session_state.solve_results=results_list
                st.session_state.solution_pool=solution_pool
                save_solution_pool(solution_pool, st.session_state.current_json)
                status.text('Scheduling completed successfully!'); progress.progress(1.0)
                time.sleep(0.5); progress.empty(); status.empty()
            else:
                st.error('No scheduling results generated')
        except Exception as e:
            st.error(f'Error during PPO solving: {e}')
            import traceback; st.error(traceback.format_exc())

def solve_with_iaoa_gns():
    """Solve using IAOA+GNS algorithm."""
    if not st.session_state.get('current_json'):
        st.error('No problem instance loaded')
        return
    
    json_data = st.session_state.current_json
    problem = yuchu_json_to_problem_instance(json_data)
    
    pop_size = st.session_state.get('iaoa_pop_size', 30)
    max_iterations = st.session_state.get('iaoa_max_iterations', 50)
    config = IAOAConfig(pop_size=pop_size, max_iterations=max_iterations)
    algorithm = IAOAGNSAlgorithm(config)
    
    num_runs = st.session_state.get('iaoa_num_runs', 1)
    results_list = []
    solution_pool = []
    
    with st.spinner('Running IAOA+GNS scheduling algorithm...'):
        progress = st.progress(0)
        status = st.empty()
        
        for run in range(num_runs):
            status.text(f'Running IAOA+GNS... ({run+1}/{num_runs})')
            progress.progress((run+1) / num_runs)
            
            solution = algorithm.solve(problem, verbose=False, timeout=600.0)
            makespan = float(solution.makespan)
            results_list.append(makespan)
            
            solution_data = solution_to_yuchu_format(solution, problem, json_data)
            
            os.makedirs('solution_pools', exist_ok=True)
            ts = time.strftime('%Y%m%d_%H%M%S')
            
            schedule_df = pd.DataFrame(solution_data['schedule'])
            csv_path = f'solution_pools/solution_pool_{ts}_run{run+1}.csv'
            schedule_df.to_csv(csv_path, index=False)
            
            solution_pool.append({
                'instance_id': run+1,
                'makespan': makespan,
                'run_number': run+1,
                'gantt_file': f'run_{run+1}_gantt_chart_instance_1.png',
                'pool_csv': csv_path,
                'pool_rows': len(schedule_df)
            })
        
        if results_list:
            st.session_state.solve_results = results_list
            st.session_state.solution_pool = solution_pool
            save_solution_pool(solution_pool, json_data)
            status.text('IAOA+GNS scheduling completed successfully!')
            progress.progress(1.0)
            time.sleep(0.5)
            progress.empty()
            status.empty()
        else:
            st.error('No scheduling results generated')

def display_results(results_list):
    st.success('Scheduling completed successfully!')
    c1,c2,c3=st.columns(3)
    with c1: st.metric('Best Makespan', f"{min(results_list):.2f}")
    with c2: st.metric('Average Makespan', f"{np.mean(results_list):.2f}")
    with c3: st.metric('Worst Makespan', f"{max(results_list):.2f}")
    st.subheader('📊 Schedule Visualization'); displayed=[]
    if getattr(st.session_state,'solution_pool',None):
        for sol in st.session_state.solution_pool:
            csv_path=sol.get('pool_csv')
            if csv_path and os.path.exists(csv_path):
                df=enrich_solution_csv(csv_path, st.session_state.get('current_json'))
                title=f"Run {sol.get('run_number')} - Makespan: {sol.get('makespan')}"
                out=generate_gantt_from_df(df,title=title)
                if out:
                    st.image(out, caption=f'Enriched Gantt - {os.path.basename(out)}', use_container_width=True)
                    displayed.append(out)
    if not displayed:
        if os.path.isdir('gantt_charts'):
            files=[f for f in os.listdir('gantt_charts') if f.endswith('.png')]
        else: files=[]
        if files:
            for f in sorted(files):
                st.image(os.path.join('gantt_charts',f), caption=f'Scheduling Result - {f}', use_container_width=True)
        else:
            st.warning('No Gantt charts were generated')
