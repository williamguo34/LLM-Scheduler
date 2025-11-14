"""
Problem Instance and Solution classes for IAOA+GNS algorithm.
Adapted from POFJSP-reproduce for Yuchu project.
"""

import numpy as np
from collections import namedtuple
from typing import List, Dict, Set, Optional
from .exceptions import ValidationError, InvalidProblemError, validate_positive_int

# Data Structures
Operation = namedtuple('Operation', ['job_idx', 'op_idx_in_job'])


class ProblemInstance:
    """Represents a POFJSP problem instance."""
    
    def __init__(self, 
                 num_jobs: int, 
                 num_machines: int, 
                 num_operations_per_job: List[int], 
                 processing_times: List[np.ndarray], 
                 predecessors_map: Dict[Operation, Set[Operation]], 
                 successors_map: Dict[Operation, Set[Operation]]):
        """Initialize the problem instance."""
        self.num_jobs = validate_positive_int(num_jobs, "num_jobs")
        self.num_machines = validate_positive_int(num_machines, "num_machines")
        
        if not isinstance(num_operations_per_job, list) or len(num_operations_per_job) != num_jobs:
            raise ValidationError(f"num_operations_per_job must be list of length {num_jobs}")
        
        for i, ops in enumerate(num_operations_per_job):
            validate_positive_int(ops, f"num_operations_per_job[{i}]")
        
        self.num_operations_per_job = num_operations_per_job
        self.total_operations = sum(num_operations_per_job)
        self.processing_times = processing_times
        self.predecessors_map = predecessors_map
        self.successors_map = successors_map
        
        # Create all operations
        self.all_operations = []
        for j in range(num_jobs):
            for o in range(num_operations_per_job[j]):
                self.all_operations.append(Operation(j, o))
    
    def get_valid_machines(self, operation: Operation) -> List[int]:
        """Get list of machines that can process the given operation."""
        if operation not in set(self.all_operations):
            raise ValidationError(f"Operation {operation} not in problem instance")
        
        job_times = self.processing_times[operation.job_idx]
        valid_machines = []
        
        for machine_idx in range(self.num_machines):
            if job_times[operation.op_idx_in_job, machine_idx] != np.inf:
                valid_machines.append(machine_idx)
        
        return valid_machines
    
    def get_processing_time(self, operation: Operation, machine_idx: int) -> float:
        """Get processing time for operation on specific machine."""
        if operation not in set(self.all_operations):
            raise ValidationError(f"Operation {operation} not in problem instance")
        
        if not 0 <= machine_idx < self.num_machines:
            raise ValidationError(f"Machine index {machine_idx} not in range [0, {self.num_machines})")
        
        return self.processing_times[operation.job_idx][operation.op_idx_in_job, machine_idx]
    
    def __repr__(self) -> str:
        return (f"ProblemInstance(jobs={self.num_jobs}, machines={self.num_machines}, "
                f"operations={self.total_operations})")


class Solution:
    """Represents a solution to a POFJSP problem."""
    
    def __init__(self, operation_sequence: List[Operation], machine_assignment: List[int]):
        """Initialize solution."""
        if not isinstance(operation_sequence, list) or not isinstance(machine_assignment, list):
            raise ValidationError("operation_sequence and machine_assignment must be lists")
        
        if len(operation_sequence) != len(machine_assignment):
            raise ValidationError(
                f"Length mismatch: operation_sequence={len(operation_sequence)}, "
                f"machine_assignment={len(machine_assignment)}"
            )
        
        self.operation_sequence = operation_sequence 
        self.machine_assignment = machine_assignment
        self.makespan = float('inf')
        self.schedule_details = {}  # {Operation: {'start_time', 'end_time', 'machine'}}
        self.machine_schedules = []  # Will be initialized in decode_solution
    
    def __lt__(self, other: 'Solution') -> bool:
        """For sorting solutions by makespan."""
        return self.makespan < other.makespan
    
    def __repr__(self) -> str:
        return f"Solution(makespan={self.makespan:.2f}, operations={len(self.operation_sequence)})"

