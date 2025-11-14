"""
Solution decoder for IAOA+GNS algorithm.
Adapted from POFJSP-reproduce for Yuchu project.
"""

import numpy as np
from typing import List, Dict, Tuple
from .problem_instance import ProblemInstance, Solution, Operation
from .exceptions import ValidationError, InvalidMachineAssignmentError, PrecedenceConstraintViolationError


def decode_solution(solution: Solution, problem: ProblemInstance, verbose: bool = False) -> Tuple[float, Dict, List]:
    """
    Decodes a solution to calculate makespan and schedule details.
    
    Args:
        solution: Solution object with operation sequence and machine assignments
        problem: Problem instance with constraints and processing times
        verbose: Enable detailed logging
        
    Returns:
        Tuple of (makespan, schedule_details, machine_schedules)
    """
    if solution is None or problem is None:
        raise ValidationError("solution and problem cannot be None")
    
    if not hasattr(solution, 'operation_sequence') or not hasattr(solution, 'machine_assignment'):
        raise ValidationError("solution must have operation_sequence and machine_assignment")
    
    if len(solution.operation_sequence) != len(solution.machine_assignment):
        raise ValidationError(
            f"Sequence length {len(solution.operation_sequence)} != assignment length {len(solution.machine_assignment)}"
        )
    
    try:
        return _decode_solution_implementation(solution, problem, verbose)
    except Exception as e:
        # Return safe fallback values
        solution.makespan = float('inf')
        solution.schedule_details = {}
        solution.machine_schedules = [[] for _ in range(problem.num_machines)]
        return float('inf'), {}, [[] for _ in range(problem.num_machines)]


def _decode_solution_implementation(solution: Solution, problem: ProblemInstance, verbose: bool) -> Tuple[float, Dict, List]:
    """Internal implementation of solution decoding."""
    operation_objects = solution.operation_sequence
    
    # Validate all machine assignments
    for i, machine_idx in enumerate(solution.machine_assignment):
        if not isinstance(machine_idx, int) or not (0 <= machine_idx < problem.num_machines):
            op = operation_objects[i] if i < len(operation_objects) else f"op_{i}"
            raise InvalidMachineAssignmentError(op, machine_idx, "Invalid machine index")
    
    schedule_details = {}
    machine_schedules = [[] for _ in range(problem.num_machines)]
    
    # Keep track of completion times of operations for precedence constraints
    operation_completion_times = {}
    scheduled_operations = set()
    
    # Create a graph of operation dependencies
    in_degree = {op: 0 for op in operation_objects}
    op_to_predecessors = {}
    
    for op in operation_objects:
        if op in problem.predecessors_map:
            op_to_predecessors[op] = problem.predecessors_map[op]
            in_degree[op] = len(problem.predecessors_map[op])
        else:
            op_to_predecessors[op] = []
    
    # Find operations with no predecessors
    ready_operations = [op for op in operation_objects if in_degree[op] == 0]
    
    if not ready_operations:
        raise PrecedenceConstraintViolationError(
            "No operations without predecessors", list(operation_objects)
        )
    
    # Process operations in topological order
    processed_ops = 0
    max_iterations = len(operation_objects) * 2
    iterations = 0
    
    while ready_operations and processed_ops < len(operation_objects) and iterations < max_iterations:
        iterations += 1
        current_op = ready_operations.pop(0)
        
        if current_op in scheduled_operations:
            continue
        
        # Find its index in the operation sequence
        op_idx = operation_objects.index(current_op)
        assigned_machine = solution.machine_assignment[op_idx]
        proc_time = problem.processing_times[current_op.job_idx][current_op.op_idx_in_job, assigned_machine]
        
        # Validate machine assignment
        if not (0 <= assigned_machine < problem.num_machines):
            raise InvalidMachineAssignmentError(
                current_op, assigned_machine, "Machine index out of range"
            )
        
        if proc_time == np.inf or proc_time < 0:
            raise InvalidMachineAssignmentError(
                current_op, assigned_machine, proc_time
            )
        
        # Determine earliest start time based on predecessors
        earliest_start_due_to_predecessors = 0
        if current_op in op_to_predecessors:
            for pred_op in op_to_predecessors[current_op]:
                if pred_op in operation_completion_times:
                    earliest_start_due_to_predecessors = max(
                        earliest_start_due_to_predecessors,
                        operation_completion_times[pred_op]
                    )
        
        # Sort machine schedule by start times to find gaps
        machine_schedules[assigned_machine].sort()
        
        # Try to insert in existing gaps
        last_finish_time_on_machine = 0
        inserted = False
        for j in range(len(machine_schedules[assigned_machine])):
            gap_start = last_finish_time_on_machine
            gap_end = machine_schedules[assigned_machine][j][0]
            
            possible_start_in_gap = max(earliest_start_due_to_predecessors, gap_start)
            if possible_start_in_gap + proc_time <= gap_end:
                op_start_time = possible_start_in_gap
                inserted = True
                break
            last_finish_time_on_machine = machine_schedules[assigned_machine][j][1]
        
        if not inserted:
            # If no suitable gap, schedule after the last operation on the machine
            op_start_time = max(earliest_start_due_to_predecessors, last_finish_time_on_machine)
        
        op_end_time = op_start_time + proc_time
        
        # Update schedules
        machine_schedules[assigned_machine].append((op_start_time, op_end_time))
        machine_schedules[assigned_machine].sort()
        
        schedule_details[current_op] = {
            'start_time': op_start_time,
            'end_time': op_end_time,
            'machine': assigned_machine
        }
        operation_completion_times[current_op] = op_end_time
        scheduled_operations.add(current_op)
        
        # Update successors' in_degree and add to ready queue
        if current_op in problem.successors_map:
            for succ_op in problem.successors_map[current_op]:
                if succ_op in in_degree:
                    in_degree[succ_op] -= 1
                    if in_degree[succ_op] == 0:
                        ready_operations.append(succ_op)
        
        processed_ops += 1
    
    # Check if all operations were processed
    if processed_ops < len(operation_objects):
        if verbose:
            print(f"WARNING: Not all operations were processed.")
    
    makespan = 0
    if operation_completion_times:
        makespan = max(operation_completion_times.values())
    
    # For GNS, it's useful to have machine schedules also store op info
    final_machine_schedules_detailed = [[] for _ in range(problem.num_machines)]
    for op, details in schedule_details.items():
        final_machine_schedules_detailed[details['machine']].append(
            (details['start_time'], details['end_time'], op)
        )
    for m_idx in range(problem.num_machines):
        final_machine_schedules_detailed[m_idx].sort()
    
    solution.makespan = makespan
    solution.schedule_details = schedule_details
    solution.machine_schedules = final_machine_schedules_detailed
    return makespan, schedule_details, final_machine_schedules_detailed

