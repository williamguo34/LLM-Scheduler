"""
Solution Pool utilities for IAOA+GNS algorithm.
Compatible with PPO solution pool format and data structures.
"""

import csv
import os
import random
import numpy as np
from typing import List, Dict, Optional
from .problem_instance import Solution, ProblemInstance
from .iaoa_gns import IAOAGNSAlgorithm, IAOAConfig


def solution_to_csv_rows(solution: Solution, instance_id: int = 1) -> List[Dict]:
    """
    Convert IAOA+GNS Solution to CSV rows matching PPO format.
    
    CSV format: instance_id, job, operation, machine, start_time, end_time, duration
    
    Args:
        solution: IAOA+GNS Solution object
        instance_id: Instance/run ID (default: 1)
        
    Returns:
        List of dictionaries, each representing one operation schedule row
    """
    rows = []
    
    if not solution.schedule_details:
        return rows
    
    for op, details in solution.schedule_details.items():
        start_time = details['start_time']
        end_time = details['end_time']
        duration = end_time - start_time
        
        rows.append({
            'instance_id': instance_id,
            'job': op.job_idx + 1,  # Convert to 1-indexed
            'operation': op.op_idx_in_job,  # Keep 0-indexed (matches PPO)
            'machine': details['machine'] + 1,  # Convert to 1-indexed
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        })
    
    return rows


def save_solution_pool_csv(solutions: List[Solution], csv_path: str, base_instance_id: int = 1) -> int:
    """
    Save multiple solutions to CSV file in PPO-compatible format.
    
    Each solution gets its own instance_id (base_instance_id + solution_index).
    This allows multiple solutions in one CSV file while keeping them distinct.
    
    Args:
        solutions: List of Solution objects
        csv_path: Path to save CSV file
        base_instance_id: Base instance ID (each solution gets base_instance_id + index)
        
    Returns:
        Number of rows written
    """
    all_rows = []
    
    for sol_idx, solution in enumerate(solutions):
        instance_id = base_instance_id + sol_idx
        rows = solution_to_csv_rows(solution, instance_id=instance_id)
        all_rows.extend(rows)
    
    if not all_rows:
        return 0
    
    os.makedirs(os.path.dirname(csv_path) if os.path.dirname(csv_path) else '.', exist_ok=True)
    
    fieldnames = ['instance_id', 'job', 'operation', 'machine', 'start_time', 'end_time', 'duration']
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    
    return len(all_rows)


def solve_with_pool(problem: ProblemInstance, 
                   config: Optional[IAOAConfig] = None,
                   num_runs: int = 1,
                   pool_size: int = 10,
                   use_final_population: bool = True) -> Dict:
    """
    Solve problem with IAOA+GNS and return solution pool.
    
    Compatible with PPO solution pool format:
    - Returns list of solutions with makespan, CSV path, etc.
    - Supports single-run (final population) or multi-run (ensemble)
    
    Args:
        problem: ProblemInstance to solve
        config: IAOA+GNS configuration (uses defaults if None)
        num_runs: Number of independent runs (for ensemble)
        pool_size: Maximum number of solutions to return per run
        use_final_population: If True, return top-K from final population (single run only)
        
    Returns:
        Dictionary with:
        - 'solutions': List of Solution objects
        - 'makespans': List of makespan values
        - 'best_solution': Best solution found
        - 'best_makespan': Best makespan value
    """
    config = config or IAOAConfig()
    all_solutions = []
    all_makespans = []
    
    for run in range(num_runs):
        # Set different seed for each run to ensure diversity
        seed = 42 + run * 17
        random.seed(seed)
        np.random.seed(seed)
        
        algorithm = IAOAGNSAlgorithm(config)
        
        if use_final_population and num_runs == 1:
            # Single run: get top-K from final population
            best_solution, population = algorithm.solve(problem, verbose=False, timeout=600.0, return_population=True)
            sorted_pop = sorted(population, key=lambda s: s.makespan)
            pool = sorted_pop[:min(pool_size, len(sorted_pop))]
            all_solutions.extend(pool)
            all_makespans.extend([s.makespan for s in pool])
        else:
            # Multi-run: collect best solution from each run
            solution = algorithm.solve(problem, verbose=False, timeout=600.0)
            all_solutions.append(solution)
            all_makespans.append(solution.makespan)
    
    # Find best solution
    best_idx = np.argmin(all_makespans)
    best_solution = all_solutions[best_idx]
    best_makespan = all_makespans[best_idx]
    
    return {
        'solutions': all_solutions,
        'makespans': all_makespans,
        'best_solution': best_solution,
        'best_makespan': best_makespan,
        'num_solutions': len(all_solutions)
    }

