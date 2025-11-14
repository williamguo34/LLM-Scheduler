"""
IAOA+GNS Algorithm for POFJSP

Implements the Improved Adaptive Optimization Algorithm with Grade Neighborhood Search
for solving Partially Ordered Flexible Job Shop Problems (POFJSP).

Adapted from POFJSP-reproduce for Yuchu project.
"""

import numpy as np
import random
import copy
import time
import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from .problem_instance import Operation, ProblemInstance, Solution
from .decoder import decode_solution
from .exceptions import AlgorithmError, ValidationError, ConvergenceError, validate_positive_int

logger = logging.getLogger(__name__)


@dataclass
class IAOAConfig:
    """Configuration for IAOA+GNS algorithm."""
    pop_size: int = 80
    max_iterations: int = 60
    moa_min: float = 0.2
    moa_max: float = 1.0
    
    def __post_init__(self):
        validate_positive_int(self.pop_size, "pop_size")
        validate_positive_int(self.max_iterations, "max_iterations")
        if not 0 <= self.moa_min <= self.moa_max <= 1:
            raise ValidationError(f"Invalid MOA range: [{self.moa_min}, {self.moa_max}]")


class PopulationManager:
    """Handles population initialization and management."""
    
    def __init__(self, config: IAOAConfig):
        self.config = config
    
    def initialize_population(self, problem: ProblemInstance) -> List[Solution]:
        """Initialize population with diverse solutions."""
        population = []
        
        for i in range(self.config.pop_size):
            try:
                # Generate valid operation sequence
                operation_sequence = self._generate_operation_sequence(problem)
                
                # Generate machine assignment
                machine_assignment = self._generate_machine_assignment(operation_sequence, problem)
                
                # Create and evaluate solution
                solution = Solution(operation_sequence, machine_assignment)
                decode_solution(solution, problem)
                
                population.append(solution)
                
            except Exception as e:
                # Fallback to simple random solution
                operation_sequence = self._simple_random_sequence(problem)
                machine_assignment = self._simple_random_assignment(operation_sequence, problem)
                solution = Solution(operation_sequence, machine_assignment)
                decode_solution(solution, problem)
                population.append(solution)
        
        return population
    
    def _generate_operation_sequence(self, problem: ProblemInstance) -> List[Operation]:
        """Generate valid operation sequence using topological sort."""
        in_degree = {op: 0 for op in problem.all_operations}
        adj = {op: [] for op in problem.all_operations}
        
        # Build adjacency list
        for op, preds in problem.predecessors_map.items():
            in_degree[op] = len(preds)
            for pred_op in preds:
                if pred_op in adj:
                    adj[pred_op].append(op)
        
        # Kahn's algorithm with randomization
        queue = [op for op in problem.all_operations if in_degree[op] == 0]
        random.shuffle(queue)
        
        sequence = []
        while queue:
            current = queue.pop(0)
            sequence.append(current)
            
            successors = list(adj[current])
            random.shuffle(successors)
            
            for successor in successors:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)
        
        if len(sequence) != problem.total_operations:
            return self._simple_random_sequence(problem)
        
        return sequence
    
    def _generate_machine_assignment(self, sequence: List[Operation], problem: ProblemInstance) -> List[int]:
        """Generate machine assignment with load balancing."""
        assignment = []
        machine_loads = [0.0] * problem.num_machines
        
        for op in sequence:
            valid_machines = problem.get_valid_machines(op)
            
            if not valid_machines:
                assignment.append(0)  # Fallback
                continue
            
            # Choose machine with lowest current load
            best_machine = min(valid_machines, 
                             key=lambda m: machine_loads[m] + problem.get_processing_time(op, m))
            
            assignment.append(best_machine)
            machine_loads[best_machine] += problem.get_processing_time(op, best_machine)
        
        return assignment
    
    def _simple_random_sequence(self, problem: ProblemInstance) -> List[Operation]:
        """Fallback: simple random sequence."""
        sequence = list(problem.all_operations)
        random.shuffle(sequence)
        return sequence
    
    def _simple_random_assignment(self, sequence: List[Operation], problem: ProblemInstance) -> List[int]:
        """Fallback: simple random assignment."""
        assignment = []
        for op in sequence:
            valid_machines = problem.get_valid_machines(op)
            assignment.append(random.choice(valid_machines) if valid_machines else 0)
        return assignment


class CrossoverOperator:
    """Handles two-dimensional clustering crossover operations."""
    
    def __init__(self, config: IAOAConfig):
        self.config = config
    
    def two_d_clustering_crossover(self, 
                                 parent1: Solution, 
                                 parent2: Solution, 
                                 population: List[Solution],
                                 best_solution: Solution,
                                 problem: ProblemInstance) -> Solution:
        """Perform two-dimensional clustering crossover."""
        try:
            # Ensure parents are decoded
            if not parent1.schedule_details:
                decode_solution(parent1, problem)
            if not parent2.schedule_details:
                decode_solution(parent2, problem)
            
            # Create offspring by combining sequences
            offspring_sequence = self._combine_sequences(parent1.operation_sequence, 
                                                       parent2.operation_sequence, 
                                                       problem)
            
            offspring_assignment = self._combine_assignments(parent1.machine_assignment,
                                                           parent2.machine_assignment,
                                                           offspring_sequence,
                                                           problem)
            
            offspring = Solution(offspring_sequence, offspring_assignment)
            decode_solution(offspring, problem)
            
            return offspring
            
        except Exception as e:
            # Fallback to parent1
            return copy.deepcopy(parent1)
    
    def _combine_sequences(self, seq1: List[Operation], seq2: List[Operation], 
                          problem: ProblemInstance) -> List[Operation]:
        """Combine operation sequences preserving precedence."""
        combined = []
        used_ops = set()
        
        i, j = 0, 0
        while len(combined) < len(problem.all_operations):
            # Try from seq1
            if i < len(seq1) and seq1[i] not in used_ops:
                if self._can_schedule_operation(seq1[i], combined, problem):
                    combined.append(seq1[i])
                    used_ops.add(seq1[i])
                    i += 1
                    continue
            
            # Try from seq2
            if j < len(seq2) and seq2[j] not in used_ops:
                if self._can_schedule_operation(seq2[j], combined, problem):
                    combined.append(seq2[j])
                    used_ops.add(seq2[j])
                    j += 1
                    continue
            
            # Find any available operation
            for op in problem.all_operations:
                if op not in used_ops and self._can_schedule_operation(op, combined, problem):
                    combined.append(op)
                    used_ops.add(op)
                    break
            else:
                break  # No valid operation found
            
            i += 1
            j += 1
        
        return combined
    
    def _can_schedule_operation(self, op: Operation, scheduled: List[Operation], 
                               problem: ProblemInstance) -> bool:
        """Check if operation can be scheduled given current sequence."""
        scheduled_set = set(scheduled)
        predecessors = problem.predecessors_map.get(op, set())
        return predecessors.issubset(scheduled_set)
    
    def _combine_assignments(self, assign1: List[int], assign2: List[int],
                           sequence: List[Operation], problem: ProblemInstance) -> List[int]:
        """Combine machine assignments."""
        assignment = []
        
        for i, op in enumerate(sequence):
            # Choose assignment that gives better processing time
            machines = []
            if i < len(assign1):
                machines.append(assign1[i])
            if i < len(assign2):
                machines.append(assign2[i])
            
            valid_machines = problem.get_valid_machines(op)
            available_machines = [m for m in machines if m in valid_machines]
            
            if available_machines:
                best_machine = min(available_machines, 
                                 key=lambda m: problem.get_processing_time(op, m))
                assignment.append(best_machine)
            elif valid_machines:
                assignment.append(random.choice(valid_machines))
            else:
                assignment.append(0)  # Fallback
        
        return assignment


class MutationOperator:
    """Handles effective parallel mutation operations."""
    
    def __init__(self, config: IAOAConfig):
        self.config = config
    
    def effective_parallel_mutation(self, solution: Solution, problem: ProblemInstance) -> Solution:
        """Perform effective parallel mutation."""
        try:
            mutated = copy.deepcopy(solution)
            
            # Mutate operation sequence
            self._mutate_sequence(mutated, problem)
            
            # Mutate machine assignment
            self._mutate_assignment(mutated, problem)
            
            # Decode and return
            decode_solution(mutated, problem)
            return mutated
            
        except Exception as e:
            return copy.deepcopy(solution)
    
    def _mutate_sequence(self, solution: Solution, problem: ProblemInstance) -> None:
        """Mutate operation sequence while preserving precedence."""
        sequence = solution.operation_sequence
        n = len(sequence)
        
        # Try swapping adjacent operations
        for _ in range(min(5, n // 2)):  # Limit mutations
            i = random.randint(0, n - 2)
            j = i + 1
            
            # Check if swap preserves precedence
            if self._can_swap_operations(sequence[i], sequence[j], sequence, i, j, problem):
                sequence[i], sequence[j] = sequence[j], sequence[i]
    
    def _mutate_assignment(self, solution: Solution, problem: ProblemInstance) -> None:
        """Mutate machine assignments."""
        assignment = solution.machine_assignment
        sequence = solution.operation_sequence
        
        # Randomly change some assignments
        num_mutations = min(3, len(assignment) // 4)  # Limit mutations
        
        for _ in range(num_mutations):
            idx = random.randint(0, len(assignment) - 1)
            op = sequence[idx]
            valid_machines = problem.get_valid_machines(op)
            
            if len(valid_machines) > 1:
                current_machine = assignment[idx]
                new_machines = [m for m in valid_machines if m != current_machine]
                if new_machines:
                    assignment[idx] = random.choice(new_machines)
    
    def _can_swap_operations(self, op1: Operation, op2: Operation, 
                           sequence: List[Operation], pos1: int, pos2: int,
                           problem: ProblemInstance) -> bool:
        """Check if two operations can be swapped."""
        scheduled_before_pos1 = set(sequence[:pos1])
        scheduled_after_pos2 = set(sequence[pos2 + 1:])
        
        # Check op2's predecessors
        op2_preds = problem.predecessors_map.get(op2, set())
        if not op2_preds.issubset(scheduled_before_pos1):
            return False
        
        # Check op1's successors
        op1_succs = problem.successors_map.get(op1, set())
        if op1_succs.intersection(scheduled_after_pos2):
            return False
        
        return True


class NeighborhoodSearch:
    """Handles Grade Neighborhood Search operations."""
    
    def __init__(self, config: IAOAConfig):
        self.config = config
    
    def grade_neighborhood_search(self, solution: Solution, bottleneck_type: str,
                                bottleneck_id: int, problem: ProblemInstance) -> Solution:
        """Perform Grade Neighborhood Search."""
        try:
            if not solution.schedule_details:
                decode_solution(solution, problem)
            
            if bottleneck_type == "job":
                return self._job_neighborhood_search(solution, bottleneck_id, problem)
            elif bottleneck_type == "machine":
                return self._machine_neighborhood_search(solution, bottleneck_id, problem)
            else:
                return copy.deepcopy(solution)
                
        except Exception as e:
            return copy.deepcopy(solution)
    
    def _job_neighborhood_search(self, solution: Solution, job_id: int, 
                               problem: ProblemInstance) -> Solution:
        """Neighborhood search focused on bottleneck job."""
        best_solution = copy.deepcopy(solution)
        
        # Find operations of bottleneck job
        job_operations = [i for i, op in enumerate(solution.operation_sequence) 
                         if op.job_idx == job_id]
        
        # Try different machine assignments for job operations
        for op_idx in job_operations:
            op = solution.operation_sequence[op_idx]
            valid_machines = problem.get_valid_machines(op)
            
            for machine in valid_machines:
                if machine != solution.machine_assignment[op_idx]:
                    # Create modified solution
                    modified = copy.deepcopy(solution)
                    modified.machine_assignment[op_idx] = machine
                    decode_solution(modified, problem)
                    
                    if modified.makespan < best_solution.makespan:
                        best_solution = modified
        
        return best_solution
    
    def _machine_neighborhood_search(self, solution: Solution, machine_id: int,
                                   problem: ProblemInstance) -> Solution:
        """Neighborhood search focused on bottleneck machine."""
        best_solution = copy.deepcopy(solution)
        
        # Find operations assigned to bottleneck machine
        machine_operations = [i for i, machine in enumerate(solution.machine_assignment)
                            if machine == machine_id]
        
        # Try reassigning operations to other machines
        for op_idx in machine_operations:
            op = solution.operation_sequence[op_idx]
            valid_machines = problem.get_valid_machines(op)
            
            for machine in valid_machines:
                if machine != machine_id:
                    # Create modified solution
                    modified = copy.deepcopy(solution)
                    modified.machine_assignment[op_idx] = machine
                    decode_solution(modified, problem)
                    
                    if modified.makespan < best_solution.makespan:
                        best_solution = modified
        
        return best_solution


class BottleneckDetector:
    """Detects bottleneck jobs and machines in solutions."""
    
    @staticmethod
    def find_bottlenecks(solution: Solution, problem: ProblemInstance) -> Tuple[int, int]:
        """Find bottleneck job and machine indices."""
        if not solution.schedule_details:
            decode_solution(solution, problem)
        
        # Find bottleneck job (longest completion time)
        job_finish_times = [0.0] * problem.num_jobs
        for op, details in solution.schedule_details.items():
            job_finish_times[op.job_idx] = max(job_finish_times[op.job_idx], details['end_time'])
        
        bottleneck_job = np.argmax(job_finish_times) if any(job_finish_times) else -1
        
        # Find bottleneck machine (highest utilization)
        machine_finish_times = [0.0] * problem.num_machines
        for m_idx in range(problem.num_machines):
            if solution.machine_schedules and m_idx < len(solution.machine_schedules):
                if solution.machine_schedules[m_idx]:
                    machine_finish_times[m_idx] = max(op_details[1] 
                                                    for op_details in solution.machine_schedules[m_idx])
        
        bottleneck_machine = np.argmax(machine_finish_times) if any(machine_finish_times) else -1
        
        return bottleneck_job, bottleneck_machine


class IAOAGNSAlgorithm:
    """
    IAOA+GNS Algorithm for POFJSP.
    
    Improved Adaptive Optimization Algorithm with Grade Neighborhood Search
    for solving Partially Ordered Flexible Job Shop Problems.
    """
    
    def __init__(self, config: Optional[IAOAConfig] = None):
        """Initialize algorithm with configuration."""
        self.config = config or IAOAConfig()
        
        # Initialize components
        self.population_manager = PopulationManager(self.config)
        self.crossover_operator = CrossoverOperator(self.config)
        self.mutation_operator = MutationOperator(self.config)
        self.neighborhood_search = NeighborhoodSearch(self.config)
        
        logger.info(f"Initialized IAOA+GNS with config: {self.config}")
    
    @property
    def algorithm_name(self) -> str:
        """Return the algorithm name."""
        return "IAOA+GNS"
    
    def solve(self, problem: ProblemInstance, verbose: bool = False, timeout: float = 300.0):
        """
        Solve POFJSP instance using IAOA+GNS.
        
        Args:
            problem: Problem instance to solve
            verbose: Enable detailed logging
            timeout: Maximum execution time in seconds
            
        Returns:
            Best solution found
        """
        try:
            start_time = time.time()
            
            logger.info(f"Starting IAOA+GNS on problem: {problem}")
            
            # Initialize population
            population = self._initialize_population(problem, verbose)
            best_solution = min(population, key=lambda s: s.makespan)
            initial_makespan = best_solution.makespan
            
            if verbose:
                print(f"Initial best makespan: {initial_makespan:.2f}")
            
            # Main optimization loop
            iteration = 0
            for iteration in range(self.config.max_iterations):
                # Check timeout
                if time.time() - start_time > timeout:
                    if verbose:
                        print(f"Timeout reached at iteration {iteration}")
                    break
                moa = self._calculate_moa(iteration)
                
                population = self._evolve_population(
                    population, best_solution, moa, problem, verbose, iteration
                )
                
                # Update best solution
                current_best = min(population, key=lambda s: s.makespan)
                if current_best.makespan < best_solution.makespan:
                    best_solution = copy.deepcopy(current_best)
                    if verbose:
                        improvement = ((initial_makespan - best_solution.makespan) / initial_makespan) * 100
                        print(f"Iter {iteration + 1}: New best = {best_solution.makespan:.2f} "
                              f"({improvement:.1f}% improvement)")
            
            logger.info(f"Algorithm completed. Final makespan: {best_solution.makespan:.2f}")
            
            return best_solution
            
        except Exception as e:
            raise AlgorithmError(f"IAOA+GNS algorithm failed: {e}")
    
    def _initialize_population(self, problem: ProblemInstance, verbose: bool) -> List[Solution]:
        """Initialize population with diverse solutions."""
        if verbose:
            print("Initializing population...")
        
        try:
            population = self.population_manager.initialize_population(problem)
            
            if not population:
                raise AlgorithmError("Failed to create initial population")
            
            # Validate population
            valid_population = []
            for solution in population:
                if solution.makespan != float('inf'):
                    valid_population.append(solution)
            
            if not valid_population:
                raise AlgorithmError("No valid solutions in initial population")
            
            if verbose:
                makespans = [s.makespan for s in valid_population]
                print(f"Population initialized: {len(valid_population)} solutions, "
                      f"makespan range: [{min(makespans):.2f}, {max(makespans):.2f}]")
            
            return valid_population
            
        except Exception as e:
            raise AlgorithmError(f"Population initialization failed: {e}")
    
    def _calculate_moa(self, iteration: int) -> float:
        """Calculate MOA (Metropolis Optimization Algorithm) parameter."""
        return self.config.moa_min + iteration * (
            (self.config.moa_max - self.config.moa_min) / self.config.max_iterations
        )
    
    def _evolve_population(self, 
                         population: List[Solution], 
                         best_solution: Solution,
                         moa: float,
                         problem: ProblemInstance,
                         verbose: bool,
                         iteration: int) -> List[Solution]:
        """Evolve population for one generation."""
        new_population = []
        
        for i, current_solution in enumerate(population):
            try:
                offspring = self._generate_offspring(
                    current_solution, population, best_solution, moa, problem, i, verbose
                )
                
                # Elitism: keep better solution
                if offspring.makespan <= current_solution.makespan:
                    new_population.append(offspring)
                    if verbose and offspring.makespan < current_solution.makespan:
                        print(f"  Solution {i}: Improved {current_solution.makespan:.2f} -> {offspring.makespan:.2f}")
                else:
                    new_population.append(current_solution)
                    
            except Exception as e:
                logger.warning(f"Error evolving solution {i}: {e}")
                new_population.append(current_solution)  # Keep original on error
        
        return new_population
    
    def _generate_offspring(self,
                          current_solution: Solution,
                          population: List[Solution],
                          best_solution: Solution,
                          moa: float,
                          problem: ProblemInstance,
                          solution_idx: int,
                          verbose: bool) -> Solution:
        """Generate offspring using IAOA operators."""
        r1, r2, r3 = random.random(), random.random(), random.random()
        
        if r1 > moa:  # Exploration phase
            if r2 > 0.5:  # Crossover
                parent2 = self._select_parent(population, solution_idx)
                if verbose:
                    print(f"  Solution {solution_idx}: 2D clustering crossover")
                
                return self.crossover_operator.two_d_clustering_crossover(
                    current_solution, parent2, population, best_solution, problem
                )
            else:  # Mutation
                if verbose:
                    print(f"  Solution {solution_idx}: Effective parallel mutation")
                
                return self.mutation_operator.effective_parallel_mutation(
                    current_solution, problem
                )
        else:  # Development phase (GNS)
            bottleneck_job, bottleneck_machine = BottleneckDetector.find_bottlenecks(
                current_solution, problem
            )
            
            if r3 > 0.5 and bottleneck_job != -1:  # Job GNS
                if verbose:
                    print(f"  Solution {solution_idx}: Job GNS on job {bottleneck_job}")
                
                return self.neighborhood_search.grade_neighborhood_search(
                    current_solution, "job", bottleneck_job, problem
                )
            elif bottleneck_machine != -1:  # Machine GNS
                if verbose:
                    print(f"  Solution {solution_idx}: Machine GNS on machine {bottleneck_machine}")
                
                return self.neighborhood_search.grade_neighborhood_search(
                    current_solution, "machine", bottleneck_machine, problem
                )
            else:  # No bottleneck found, return copy
                if verbose:
                    print(f"  Solution {solution_idx}: No bottleneck found, using copy")
                return copy.deepcopy(current_solution)
    
    def _select_parent(self, population: List[Solution], exclude_idx: int) -> Solution:
        """Select second parent for crossover."""
        available_indices = [i for i in range(len(population)) if i != exclude_idx]
        if not available_indices:
            return population[exclude_idx]  # Fallback
        
        return population[random.choice(available_indices)]

