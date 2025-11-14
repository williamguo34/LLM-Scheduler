"""
Adapter to convert Yuchu JSON format to ProblemInstance format for IAOA+GNS algorithm.
"""

import numpy as np
from typing import Dict, List, Set
from .problem_instance import ProblemInstance, Operation
from .exceptions import ValidationError


def yuchu_json_to_problem_instance(json_data: Dict) -> ProblemInstance:
    """
    Convert Yuchu JSON format to ProblemInstance.
    
    Yuchu format:
    {
        "J": <num_jobs>,
        "M": <num_machines>,
        "instances": [
            {
                "job_id": <id>,
                "job_n": <name>,
                "operations": [
                    {
                        "op_id": <id>,
                        "re": "<machine>:<time>|...",  # e.g., "1:5.0|2:6.0" or "1&2:5.0"
                        "pre": [<op_id>, ...]  # optional precedence
                    }
                ]
            }
        ]
    }
    
    Returns:
        ProblemInstance object
    """
    try:
        num_jobs = json_data['J']
        num_machines = json_data['M']
        instances = json_data.get('instances', [])
        
        if len(instances) != num_jobs:
            raise ValidationError(f"Expected {num_jobs} jobs, got {len(instances)}")
        
        # Build operation mapping: op_id -> (job_idx, op_idx_in_job)
        op_id_to_operation = {}
        job_operations = {}  # job_idx -> list of operations
        
        num_operations_per_job = []
        processing_times = []
        
        for job_idx, job_data in enumerate(instances):
            job_id = job_data.get('job_id', job_idx + 1)
            operations = job_data.get('operations', [])
            num_operations_per_job.append(len(operations))
            
            job_processing_times = np.full((len(operations), num_machines), np.inf)
            job_ops = []
            
            for op_idx, op_data in enumerate(operations):
                op_id = op_data.get('op_id', f"job_{job_id}_op_{op_idx}")
                op = Operation(job_idx, op_idx)
                op_id_to_operation[op_id] = op
                job_ops.append(op)
                
                # Parse processing times from 're' field
                re_field = op_data.get('re', '')
                _parse_processing_times(re_field, job_processing_times, op_idx, num_machines)
            
            job_operations[job_idx] = job_ops
            processing_times.append(job_processing_times)
        
        # Build precedence constraints
        predecessors_map = {op: set() for op_list in job_operations.values() for op in op_list}
        successors_map = {op: set() for op_list in job_operations.values() for op in op_list}
        
        for job_idx, job_data in enumerate(instances):
            operations = job_data.get('operations', [])
            
            for op_idx, op_data in enumerate(operations):
                op_id = op_data.get('op_id', f"job_{job_idx+1}_op_{op_idx}")
                op = op_id_to_operation.get(op_id)
                
                if op is None:
                    continue
                
                # Parse precedence constraints
                pre_op_ids = op_data.get('pre', [])
                for pre_op_id in pre_op_ids:
                    pre_op = op_id_to_operation.get(pre_op_id)
                    if pre_op is not None:
                        predecessors_map[op].add(pre_op)
                        successors_map[pre_op].add(op)
        
        return ProblemInstance(
            num_jobs=num_jobs,
            num_machines=num_machines,
            num_operations_per_job=num_operations_per_job,
            processing_times=processing_times,
            predecessors_map=predecessors_map,
            successors_map=successors_map
        )
        
    except Exception as e:
        raise ValidationError(f"Failed to convert Yuchu JSON to ProblemInstance: {e}")


def _parse_processing_times(re_field: str, job_processing_times: np.ndarray, 
                            op_idx: int, num_machines: int) -> None:
    """
    Parse processing times from 're' field.
    
    Formats supported:
    - "1:5.0" - single machine
    - "1:5.0|2:6.0" - multiple machines (OR)
    - "1&2:5.0" - parallel machines (AND)
    """
    if not re_field or ':' not in re_field:
        return
    
    # Handle OR (|) - multiple machine options
    if '|' in re_field:
        for option in re_field.split('|'):
            if ':' in option:
                machine_part, time_part = option.split(':', 1)
                try:
                    machine_id = int(machine_part.strip()) - 1  # Convert to 0-indexed
                    time_val = float(time_part.strip())
                    if 0 <= machine_id < num_machines:
                        job_processing_times[op_idx, machine_id] = time_val
                except (ValueError, IndexError):
                    continue
    
    # Handle AND (&) - parallel machines
    elif '&' in re_field and ':' in re_field:
        machines_part, time_part = re_field.split(':', 1)
        try:
            time_val = float(time_part.strip())
            machine_ids = [int(m.strip()) - 1 for m in machines_part.split('&') if m.strip()]
            for machine_id in machine_ids:
                if 0 <= machine_id < num_machines:
                    job_processing_times[op_idx, machine_id] = time_val
        except (ValueError, IndexError):
            pass
    
    # Handle single machine
    elif ':' in re_field:
        machine_part, time_part = re_field.split(':', 1)
        try:
            machine_id = int(machine_part.strip()) - 1  # Convert to 0-indexed
            time_val = float(time_part.strip())
            if 0 <= machine_id < num_machines:
                job_processing_times[op_idx, machine_id] = time_val
        except (ValueError, IndexError):
            pass


def solution_to_yuchu_format(solution, problem: ProblemInstance, json_data: Dict) -> Dict:
    """
    Convert Solution back to Yuchu format for display.
    
    Returns:
        Dictionary with solution details in Yuchu format
    """
    schedule_data = []
    
    for op, details in solution.schedule_details.items():
        schedule_data.append({
            'job_id': op.job_idx + 1,  # Convert back to 1-indexed
            'operation': op.op_idx_in_job,
            'machine': details['machine'] + 1,  # Convert back to 1-indexed
            'start_time': details['start_time'],
            'end_time': details['end_time']
        })
    
    return {
        'makespan': solution.makespan,
        'schedule': schedule_data,
        'machine_schedules': solution.machine_schedules
    }

