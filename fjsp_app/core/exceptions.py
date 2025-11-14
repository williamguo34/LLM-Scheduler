"""
POFJSP Exception Hierarchy

Custom exceptions for Partial Order Flexible Job Shop Problem operations.
Provides structured error handling across all modules.
"""


class POFJSPError(Exception):
    """Base exception for all POFJSP-related errors."""
    pass


class ValidationError(POFJSPError):
    """Raised when input validation fails."""
    pass


class InvalidProblemError(ValidationError):
    """Raised when problem instance is invalid or malformed."""
    
    def __init__(self, problem_type: str, details: str):
        self.problem_type = problem_type
        self.details = details
        super().__init__(f"Invalid {problem_type} problem: {details}")


class InvalidMachineAssignmentError(POFJSPError):
    """Raised when an operation is assigned to an incompatible machine."""
    
    def __init__(self, operation, machine_id: int, processing_time):
        self.operation = operation
        self.machine_id = machine_id
        self.processing_time = processing_time
        super().__init__(
            f"Operation {operation} cannot be processed on machine {machine_id} "
            f"(processing time: {processing_time})"
        )


class PrecedenceConstraintViolationError(POFJSPError):
    """Raised when precedence constraints are violated."""
    
    def __init__(self, operation, violated_predecessors: list):
        self.operation = operation
        self.violated_predecessors = violated_predecessors
        super().__init__(
            f"Operation {operation} scheduled before required predecessors: {violated_predecessors}"
        )


class InfeasibleProblemError(POFJSPError):
    """Raised when no feasible solution exists for the problem."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Problem is infeasible: {reason}")


class AlgorithmError(POFJSPError):
    """Base class for algorithm-specific errors."""
    pass


class ConvergenceError(AlgorithmError):
    """Raised when algorithm fails to converge."""
    
    def __init__(self, algorithm_name: str, iterations: int, best_fitness: float):
        self.algorithm_name = algorithm_name
        self.iterations = iterations
        self.best_fitness = best_fitness
        super().__init__(
            f"{algorithm_name} failed to converge after {iterations} iterations "
            f"(best fitness: {best_fitness})"
        )


def validate_positive_int(value: int, name: str) -> int:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{name} must be a positive integer, got {value}")
    return value

