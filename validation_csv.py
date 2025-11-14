from epsGreedyForMch import PredictMch
from mb_agg import *
from Params import configs
from copy import deepcopy
from FJSP_Env import FJSP, DFJSP_GANTT_CHART
from mb_agg import g_pool_cal
import copy
import numpy as np
import torch
import matplotlib.pyplot as plt
from utils.device_utils import get_best_device
import os
import csv
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import json
import time
import random

# Configure default font settings
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 12

# Get device once at module level
DEVICE = get_best_device()


def adapt_data_for_model(data, target_n_j, target_n_m):
    batch_size, n_j, n_m, _ = data.shape
    if n_j == target_n_j and n_m == target_n_m:
        return data
    adapted_data = np.zeros((batch_size, target_n_j, target_n_m, target_n_m))
    j_range = min(n_j, target_n_j)
    m_range = min(n_m, target_n_m)
    adapted_data[:, :j_range, :m_range, :m_range] = data[:, :j_range, :m_range, :m_range]
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

    model_n_j = policy_job.n_j
    model_n_m = policy_job.n_m

    gantt_dir = 'gantt_charts'
    if not os.path.exists(gantt_dir):
        os.makedirs(gantt_dir)
    print(f"Gantt charts will be saved in: {os.path.abspath(gantt_dir)}")

    all_solutions = []

    def eval_model_bat(bat, i):
        C_max = []
        with torch.no_grad():
            original_data = bat.numpy()
            actual_n_j = original_data.shape[1]
            actual_n_m = original_data.shape[2]
            if actual_n_j != model_n_j or actual_n_m != model_n_m:
                data = adapt_data_for_model(original_data, model_n_j, model_n_m)
            else:
                data = original_data

            env = FJSP(n_j=model_n_j, n_m=model_n_m)
            gantt_chart = DFJSP_GANTT_CHART(model_n_j, model_n_m)

            g_pool_step = g_pool_cal(graph_pool_type=configs.graph_pool_type,
                                     batch_size=torch.Size([batch_size, model_n_j * model_n_m, model_n_j * model_n_m]),
                                     n_nodes=model_n_j * model_n_m,
                                     device=DEVICE)

            adj, fea, candidate, mask, mask_mch, dur, mch_time, job_time = env.reset(data)

            j = 0
            env_mask_mch = torch.from_numpy(np.copy(mask_mch)).to(DEVICE)
            env_dur = torch.from_numpy(np.copy(dur)).float().to(DEVICE)
            pool = None
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
                                                                                       candidate=env_candidate,
                                                                                       mask=env_mask,
                                                                                       mask_mch=env_mask_mch,
                                                                                       dur=env_dur,
                                                                                       a_index=0,
                                                                                       old_action=0,
                                                                                       mch_pool=pool,
                                                                                       old_policy=True,
                                                                                       T=1,
                                                                                       greedy=True)
                pi_mch, pool = policy_mch(action_node, hx, mask_mch_action, env_mch_time)
                mch_a = torch.multinomial(pi_mch.squeeze(-1), 1).squeeze(-1)
                adj, fea, reward, done, candidate, mask, job, _, mch_time, job_time = env.step(action.cpu().numpy(), mch_a, gantt_chart)
                j += 1
                if env.done():
                    plt.title(f'Run {run_number} - Instance {i+1} - Makespan: {env.mchsEndTimes.max(-1).max(-1)[0]:.2f}', pad=20)
                    plt.grid(True, which='both', axis='both', linestyle='--', alpha=0.7)
                    ax = plt.gca()
                    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
                    plt.tight_layout()
                    plt.savefig(os.path.join(gantt_dir, f'run_{run_number}_gantt_chart_instance_{i+1}.png'), format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
                    plt.close()
                    break
            # extract solution rows
            try:
                for job_idx in range(model_n_j):
                    for op_idx in range(model_n_m):
                        machine = int(env.m[0, job_idx, op_idx])
                        if machine < 0:
                            continue
                        end_time = float(env.temp1[0, job_idx, op_idx])
                        duration = float(data[0, job_idx, op_idx, machine])
                        start_time = end_time - duration
                        all_solutions.append({
                            'instance_id': i,
                            'job': int(job_idx),
                            'operation': int(op_idx),
                            'machine': int(machine),
                            'start_time': float(start_time),
                            'end_time': float(end_time),
                            'duration': float(duration)
                        })
            except Exception:
                pass
            cost = env.mchsEndTimes.max(-1).max(-1)
            C_max.append(cost)
        return torch.tensor(cost)

    totall_cost = torch.cat([eval_model_bat(bat, i) for i, bat in enumerate(vali_set)], 0)
    if all_solutions:
        try:
            with open('solution_pool.csv', 'w', newline='') as csvfile:
                fieldnames = ['instance_id', 'job', 'operation', 'machine', 'start_time', 'end_time', 'duration']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in all_solutions:
                    writer.writerow(row)
            print(f"Wrote {len(all_solutions)} schedule rows to solution_pool.csv")
        except Exception as e:
            print(f"Failed to write solution_pool.csv: {e}")
    return totall_cost


def enrich_solution_csv(csv_path, current_json=None):
    """Load solution CSV and attach job/op names from current_json when available.

    If current_json is None, try to auto-load the latest `instance_*.json` from `solution_pools/`.
    Returns a pandas DataFrame with added columns: job_name, op_name, resource_name.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Failed to read CSV {csv_path}: {e}")
        return None

    # If no current_json provided, try to locate the latest instance_*.json in solution_pools
    if current_json is None:
        try:
            pool_dir = 'solution_pools'
            if os.path.isdir(pool_dir):
                cand = [os.path.join(pool_dir, f) for f in os.listdir(pool_dir) if f.startswith('instance_') and f.endswith('.json')]
                if cand:
                    latest = max(cand, key=os.path.getmtime)
                    with open(latest, 'r') as jf:
                        current_json = json.load(jf)
        except Exception:
            current_json = None

    # Build machine map from current_json if available
    machine_map = {}
    if isinstance(current_json, dict):
        # Many instance files list jobs and their operations; some may include machine names or a machine map
        if 'machines' in current_json and isinstance(current_json['machines'], list):
            for m in current_json['machines']:
                try:
                    machine_map[int(m.get('id'))] = str(m.get('name'))
                except Exception:
                    continue
        elif 'machine_map' in current_json and isinstance(current_json['machine_map'], dict):
            for k, v in current_json['machine_map'].items():
                try:
                    machine_map[int(k)] = str(v)
                except Exception:
                    continue

    def default_resource_name(m):
        try:
            return f"Machine {int(m) + 1}"
        except Exception:
            return str(m)

    def get_job_name(job_idx):
        try:
            return current_json['instances'][int(job_idx)]['job_n']
        except Exception:
            return f"Job {int(job_idx)+1}"

    def get_op_name(job_idx, op_idx):
        try:
            return current_json['instances'][int(job_idx)]['operations'][int(op_idx)]['op_n']
        except Exception:
            return f"Op {int(op_idx)+1}"

    # Normalize common alternate column names before enforcing schema
    if 'job' not in df.columns and 'job_id' in df.columns:
        df['job'] = df['job_id'].apply(lambda v: int(v) - 1 if pd.notna(v) else 0)
    if 'operation' not in df.columns and 'operation_id' in df.columns:
        df['operation'] = df['operation_id']
    if 'machine' not in df.columns and 'machine_id' in df.columns:
        df['machine'] = df['machine_id'].apply(lambda v: int(v) - 1 if pd.notna(v) else 0)

    # Ensure expected columns exist and compute duration if necessary
    for col in ['job', 'operation', 'machine', 'start_time', 'duration']:
        if col not in df.columns:
            if col == 'duration' and 'end_time' in df.columns and 'start_time' in df.columns:
                df['duration'] = df['end_time'] - df['start_time']
            else:
                df[col] = 0

    # Normalize types with safe conversion
    try:
        df['job'] = df['job'].astype(int)
        df['operation'] = df['operation'].astype(int)
        df['machine'] = df['machine'].astype(int)
        df['start_time'] = df['start_time'].astype(float)
        df['duration'] = df['duration'].astype(float)
    except Exception:
        df['job'] = df['job'].apply(lambda v: int(v) if pd.notna(v) else 0)
        df['operation'] = df['operation'].apply(lambda v: int(v) if pd.notna(v) else 0)
        df['machine'] = df['machine'].apply(lambda v: int(v) if pd.notna(v) else 0)
        df['start_time'] = df['start_time'].apply(lambda v: float(v) if pd.notna(v) else 0.0)
        df['duration'] = df['duration'].apply(lambda v: float(v) if pd.notna(v) else 0.0)

    df['job_name'] = df['job'].apply(get_job_name)
    df['op_name'] = df.apply(lambda r: get_op_name(r['job'], r['operation']), axis=1)

    def map_machine_name(m):
        try:
            if machine_map.get(int(m)+1):
                return machine_map.get(int(m)+1)
            if machine_map.get(int(m)):
                return machine_map.get(int(m))
        except Exception:
            pass
        return default_resource_name(m)

    df['resource_name'] = df['machine'].apply(map_machine_name)

    return df


def generate_gantt_from_df(df, out_path=None, title=None):
    """Generate a Gantt chart PNG from enriched DataFrame and save to out_path.

    Expects df columns: machine (int), start_time, duration, job, operation, job_name, op_name, resource_name
    Returns the path to the saved PNG, or None on failure.
    """
    if df is None or df.empty:
        print("No data to generate Gantt chart")
        return None

    machines = sorted(df['machine'].unique())
    y_map = {m: i for i, m in enumerate(machines)}

    # Give more vertical space per machine to avoid label wrapping
    fig, ax = plt.subplots(figsize=(10, max(6, len(machines) * 0.8)))

    # Small helper chart class to mirror DFJSP_GANTT_CHART style
    class CSV_GANTT_CHART:
        def __init__(self, total_n_job, ax):
            self.total_n_job = total_n_job
            self.ax = ax
            self.colors = self.colour_gen(total_n_job)

        def colour_gen(self, n):
            color_bits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
            colours = []
            random.seed(234)
            for i in range(n):
                cb = ['#']
                cb.extend(random.sample(color_bits, 6))
                colours.append(''.join(cb))
            return colours

        def gantt_plt(self, job, operation, y, start_time, dur_a, number_of_jobs=None, job_name=None, op_name=None):
            c = self.colors[job % len(self.colors)] if len(self.colors) > 0 else 'tab:blue'
            # Increase bar height to make rows less cramped
            bar_height = 0.6
            self.ax.barh(y, dur_a, bar_height, left=start_time, color=c, edgecolor='black', align='center')
            # Prefer human-readable names; combine into one line to avoid wrapping
            label_lines = []
            if job_name:
                label_lines.append(str(job_name))
            if op_name:
                label_lines.append(str(op_name))
            if not label_lines:
                label_lines = [f'J{job+1}.O{operation+1}']
            label = "\n".join(label_lines)
            self.ax.text(start_time + max(dur_a * 0.02, 0.01), y, label, va='center', ha='left', fontsize=8)


    chart = CSV_GANTT_CHART(total_n_job=df['job'].nunique() if 'job' in df.columns else 1, ax=ax)

    for _, row in df.iterrows():
        m = int(row['machine'])
        y = y_map[m]
        start = float(row['start_time'])
        dur = float(row['duration'])
        chart.gantt_plt(int(row['job']), int(row['operation']), y, start, dur,
                        job_name=row.get('job_name', ''), op_name=row.get('op_name', ''))

    ax.set_yticks([y_map[m] for m in machines])
    ax.set_yticklabels([df.loc[df['machine'] == m, 'resource_name'].iloc[0] for m in machines])
    ax.invert_yaxis()
    ax.set_xlabel('Time')
    if title:
        ax.set_title(title)
    plt.tight_layout()

    # Ensure adequate vertical limits so bars and labels have space
    ax.set_ylim(-0.5, len(machines) - 0.5)

    if out_path is None:
        if not os.path.isdir('gantt_charts'):
            os.makedirs('gantt_charts', exist_ok=True)
        out_path = os.path.join('gantt_charts', f'gantt_from_csv_{time.strftime("%Y%m%d_%H%M%S")}.png')

    out_path = os.path.abspath(out_path)
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    try:
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return out_path
    except Exception as e:
        print(f"Failed to save Gantt chart to {out_path}: {e}")
        return None
