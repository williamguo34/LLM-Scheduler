from epsGreedyForMch import PredictMch
from mb_agg import *
from Params import configs
from copy import deepcopy
from FJSP_Env import FJSP
from enhanced_gantt_chart import EnhancedFJSPGanttChart
from mb_agg import g_pool_cal
import copy
from agent_utils import sample_select_action
from agent_utils import greedy_select_action
import numpy as np
import torch
import matplotlib.pyplot as plt
from utils.device_utils import get_best_device
import os

# Set matplotlib to use a backend that doesn't require a display
import matplotlib
matplotlib.use('Agg')

# Configure default font settings
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 12

# Get device once at module level
DEVICE = get_best_device()

def adapt_data_for_model(data, target_n_j, target_n_m):
    """
    Adapts a dataset with n_j jobs and n_m machines to work with a model trained on 
    target_n_j jobs and target_n_m machines.
    
    If the data has fewer machines than the model expects, we pad with zeros.
    
    Args:
        data: numpy array of shape (batch_size, n_j, n_m, n_m)
        target_n_j: number of jobs the model expects
        target_n_m: number of machines the model expects
    
    Returns:
        adapted_data: numpy array of shape (batch_size, target_n_j, target_n_m, target_n_m)
    """
    batch_size, n_j, n_m, _ = data.shape
    
    # Check if we need to adapt
    if n_j == target_n_j and n_m == target_n_m:
        return data
    
    print(f"Adapting data from shape {data.shape} to ({batch_size}, {target_n_j}, {target_n_m}, {target_n_m})")
    
    # Initialize adapted data with zeros
    adapted_data = np.zeros((batch_size, target_n_j, target_n_m, target_n_m))
    
    # Copy over the original data
    j_range = min(n_j, target_n_j)
    m_range = min(n_m, target_n_m)
    
    # Copy the available data
    adapted_data[:, :j_range, :m_range, :m_range] = data[:, :j_range, :m_range, :m_range]
    
    # For each operation in the new dimensions, ensure there's at least one machine that can process it
    # by setting the last machine's processing time to 1 if all are 0
    for b in range(batch_size):
        for j in range(j_range):
            for m in range(m_range, target_n_m):
                if np.all(adapted_data[b, j, m] == 0):
                    adapted_data[b, j, m, -1] = 1.0
    
    return adapted_data

def validate(vali_set, batch_size, policy_jo, policy_mc, run_number=1):
    policy_job = copy.deepcopy(policy_jo)
    policy_mch = copy.deepcopy(policy_mc)
    policy_job.eval()
    policy_mch.eval()
    
    # Extract model dimensions
    model_n_j = policy_job.n_j
    model_n_m = policy_job.n_m
    
    # Create directory for Gantt charts if it doesn't exist
    gantt_dir = 'gantt_charts'
    if not os.path.exists(gantt_dir):
        os.makedirs(gantt_dir)
    print(f"Gantt charts will be saved in: {os.path.abspath(gantt_dir)}")
        
    def eval_model_bat(bat, i):
        C_max = []
        with torch.no_grad():
            original_data = bat.numpy()
            
            # Get actual data dimensions
            actual_n_j = original_data.shape[1]
            actual_n_m = original_data.shape[2]
            
            # Adapt data to model dimensions if necessary
            if actual_n_j != model_n_j or actual_n_m != model_n_m:
                print(f"Original data dimensions: {actual_n_j} jobs, {actual_n_m} machines")
                print(f"Model expects: {model_n_j} jobs, {model_n_m} machines")
                data = adapt_data_for_model(original_data, model_n_j, model_n_m)
                print(f"Adapted data dimensions: {data.shape}")
            else:
                data = original_data
            
            # Create environment with the model dimensions
            env = FJSP(n_j=model_n_j, n_m=model_n_m)
            gantt_chart = EnhancedFJSPGanttChart(model_n_j, model_n_m, style='professional')
            
            g_pool_step = g_pool_cal(graph_pool_type=configs.graph_pool_type,
                                     batch_size=torch.Size(
                                         [batch_size, model_n_j * model_n_m, model_n_j * model_n_m]),
                                     n_nodes=model_n_j * model_n_m,
                                     device=DEVICE)

            adj, fea, candidate, mask, mask_mch, dur, mch_time, job_time = env.reset(data)

            j = 0

            ep_rewards = - env.initQuality
            rewards = []
            env_mask_mch = torch.from_numpy(np.copy(mask_mch)).to(DEVICE)
            env_dur = torch.from_numpy(np.copy(dur)).float().to(DEVICE)
            pool=None
            while True:
                env_adj = aggr_obs(deepcopy(adj).to(DEVICE).to_sparse(), configs.n_j * configs.n_m)
                env_fea = torch.from_numpy(np.copy(fea)).float().to(DEVICE)
                env_fea = deepcopy(env_fea).reshape(-1, env_fea.size(-1))
                env_candidate = torch.from_numpy(np.copy(candidate)).long().to(DEVICE)
                env_mask = torch.from_numpy(np.copy(mask)).to(DEVICE)
                env_mch_time = torch.from_numpy(np.copy(mch_time)).float().to(DEVICE)
                action, a_idx, log_a, action_node, _, mask_mch_action, hx = policy_job(x=env_fea,
                                                                                               graph_pool=g_pool_step,
                                                                                               padded_nei=None,
                                                                                               adj=env_adj,
                                                                                               candidate=env_candidate
                                                                                               , mask=env_mask
                                                                                               , mask_mch=env_mask_mch
                                                                                               , dur=env_dur
                                                                                               , a_index=0
                                                                                               , old_action=0
                                                                                                ,mch_pool=pool
                                                                                               ,old_policy=True,
                                                                                                T=1
                                                                                               ,greedy=True
                                                                                               )

                pi_mch,pool = policy_mch(action_node, hx, mask_mch_action, env_mch_time)

                _, mch_a = pi_mch.squeeze(-1).max(1)
                # Allow random result
                # Machines with higher probabilities are more likely to be selected
                # but there is still a chance for machines with lower probabilities to be chosen.
                mch_a = torch.multinomial(pi_mch.squeeze(-1), 1).squeeze(-1)

                adj, fea, reward, done, candidate, mask,job,_,mch_time,job_time = env.step(action.cpu().numpy(), mch_a,gantt_chart)

                j += 1
                if env.done():
                    # Save the improved Gantt chart
                    makespan = env.mchsEndTimes.max(-1).max(-1)[0]
                    plt.title(f'FJSP Schedule - Run {run_number}, Instance {i+1} - Makespan: {makespan:.2f}', 
                             fontsize=16, fontweight='bold', pad=20)
                    plt.grid(True, alpha=0.3, linestyle='--')
                    plt.tight_layout()
                    plt.savefig(os.path.join(gantt_dir, f'improved_run_{run_number}_gantt_chart_instance_{i+1}.png'), 
                              format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
                    plt.close()
                    
                    # Generate machine trajectory visualization
                    if hasattr(gantt_chart, 'add_machine_trajectory_plot'):
                        trajectory_fig = gantt_chart.add_machine_trajectory_plot()
                        if trajectory_fig:
                            trajectory_fig.suptitle(f'Machine Trajectory Analysis - Run {run_number}, Instance {i+1}', 
                                                   fontsize=16, fontweight='bold')
                            trajectory_fig.savefig(os.path.join(gantt_dir, f'machine_trajectory_run_{run_number}_instance_{i+1}.png'), 
                                                  format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
                            plt.close(trajectory_fig)
                    
                    # Generate utilization analysis
                    if hasattr(gantt_chart, 'add_utilization_analysis'):
                        utilization_fig = gantt_chart.add_utilization_analysis()
                        if utilization_fig:
                            utilization_fig.suptitle(f'Utilization Analysis - Run {run_number}, Instance {i+1}', 
                                                    fontsize=16, fontweight='bold')
                            utilization_fig.savefig(os.path.join(gantt_dir, f'utilization_analysis_run_{run_number}_instance_{i+1}.png'), 
                                                   format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
                            plt.close(utilization_fig)
                    
                    # Print statistics
                    print(f"Instance {i+1} Statistics:")
                    print(f"  Makespan: {makespan:.2f}")
                    print(f"  Total Operations: {len(gantt_chart.operations_data)}")
                    if gantt_chart.machine_working_times:
                        avg_utilization = sum(gantt_chart.machine_working_times.values()) / len(gantt_chart.machine_working_times)
                        print(f"  Average Machine Working Time: {avg_utilization:.2f}")
                    
                    break
            cost = env.mchsEndTimes.max(-1).max(-1)
            C_max.append(cost)
        return torch.tensor(cost)

    totall_cost = torch.cat([eval_model_bat(bat,i) for i,bat in enumerate(vali_set)], 0)
    return totall_cost



if __name__ == '__main__':

    from uniform_instance import uni_instance_gen,FJSPDataset
    import numpy as np
    import time
    import argparse
    from Params import configs

    Pn_j = 10  # Number of jobs of instances to test
    Pn_m = 10  # Number of machines instances to test
    Nn_j = 10  # Number of jobs on which to be loaded net are trained
    Nn_m = 10  # Number of machines on which to be loaded net are trained
    low = -99  # LB of duration
    high = 99  # UB of duration
    seed = 200  # Cap seed for validate set generation
    n_vali = 100  # Validation set size
    load_data = False  # We'll generate random data instead of loading
    data_file = "FJSP_J10M10_test_data.npy"  # Path to the validation data file (if loading from file)

    N_JOBS_P = Pn_j
    N_MACHINES_P = Pn_m
    LOW = low
    HIGH = high
    N_JOBS_N = Nn_j
    N_MACHINES_N = Nn_m
    from torch.utils.data import DataLoader
    from PPOwithValue import PPO
    import torch
    import os
    from torch.utils.data import Dataset
    
    print(f"\nUsing device: {DEVICE}")
    
    # Use the model trained with M=10
    ppo = PPO(configs.lr, configs.gamma, configs.k_epochs, configs.eps_clip,
              n_j=N_JOBS_P,
              n_m=N_MACHINES_P,
              num_layers=configs.num_layers,
              neighbor_pooling_type=configs.neighbor_pooling_type,
              input_dim=configs.input_dim,
              hidden_dim=configs.hidden_dim,
              num_mlp_layers_feature_extract=configs.num_mlp_layers_feature_extract,
              num_mlp_layers_actor=configs.num_mlp_layers_actor,
              hidden_dim_actor=configs.hidden_dim_actor,
              num_mlp_layers_critic=configs.num_mlp_layers_critic,
              hidden_dim_critic=configs.hidden_dim_critic)

    filepath = 'saved_network'
    filepath = os.path.join(filepath, 'FJSP_J%sM%s' % (10,configs.n_m))
    filepath = os.path.join(filepath, 'best_value000')

    job_path = './{}.pth'.format('policy_job')
    mch_path = './{}.pth'.format('policy_mch')

    job_path = os.path.join(filepath,job_path)
    mch_path = os.path.join(filepath, mch_path)

    # Load state dicts with weights_only=True for security
    ppo.policy_job.load_state_dict(torch.load(job_path, weights_only=True))
    ppo.policy_mch.load_state_dict(torch.load(mch_path, weights_only=True))
    num_val = 10
    batch_size = 1
    SEEDs = [200]
    result = []

    for SEED in SEEDs:
        mean_makespan = []
        # Generate random dataset with 5 machines
        validation_m = 5  # Use 5 machines for validation
        print(f"Generating new validation dataset with {N_JOBS_P} jobs and {validation_m} machines...")
        validat_dataset = FJSPDataset(N_JOBS_P, validation_m, LOW, HIGH, num_val, SEED)
        
        # Note: We'll keep configs.n_m as 10 since that's what the model was trained with
        # Our adaptation function will handle the difference
        print(f"Model expects {N_JOBS_N} jobs and {N_MACHINES_N} machines")
        
        valid_loader = DataLoader(validat_dataset, batch_size=batch_size)
        vali_result = validate(valid_loader, batch_size, ppo.policy_job, ppo.policy_mch)
        
        print("\nValidation Results:")
        print("Individual instance makespans:")
        for i, makespan in enumerate(vali_result, 1):
            print(f"Instance {i}: {makespan:.2f}")
        print(f"\nAverage makespan: {np.array(vali_result).mean():.2f}")
        print(f"Best makespan: {np.array(vali_result).min():.2f}")
        print(f"Worst makespan: {np.array(vali_result).max():.2f}")

    # print(min(result))

