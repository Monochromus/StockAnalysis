"""Base class for parameter optimizers."""

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional
import threading


class OptimizationStatus(str, Enum):
    """Optimization status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OptimizationProgress:
    """Progress tracking for optimization runs."""
    optimization_id: str
    status: OptimizationStatus
    current_trial: int
    total_trials: int
    best_alpha: float
    best_params: Dict[str, Any]
    elapsed_seconds: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "optimization_id": self.optimization_id,
            "status": self.status.value,
            "current_trial": self.current_trial,
            "total_trials": self.total_trials,
            "best_alpha": self.best_alpha,
            "best_params": self.best_params,
            "elapsed_seconds": self.elapsed_seconds,
            "message": self.message,
        }


@dataclass
class OptimizationResult:
    """Final results of an optimization run."""
    success: bool
    best_params: Dict[str, Any]
    best_alpha: float
    best_sharpe: float
    best_total_return: float
    best_max_drawdown: float
    total_trials_evaluated: int
    optimization_time_seconds: float
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "best_params": self.best_params,
            "best_alpha": self.best_alpha,
            "best_sharpe": self.best_sharpe,
            "best_total_return": self.best_total_return,
            "best_max_drawdown": self.best_max_drawdown,
            "total_trials_evaluated": self.total_trials_evaluated,
            "optimization_time_seconds": self.optimization_time_seconds,
            "error_message": self.error_message,
        }


class OptimizationStore:
    """Thread-safe storage for optimization runs."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._optimizations: Dict[str, Dict[str, Any]] = {}
                    cls._instance._store_lock = threading.Lock()
        return cls._instance

    def create(self, optimization_id: str, optimizer_type: str) -> None:
        """Create a new optimization entry."""
        with self._store_lock:
            self._optimizations[optimization_id] = {
                "type": optimizer_type,
                "progress": None,
                "result": None,
                "cancel_requested": False,
            }

    def update_progress(self, optimization_id: str, progress: OptimizationProgress) -> None:
        """Update progress for an optimization."""
        with self._store_lock:
            if optimization_id in self._optimizations:
                self._optimizations[optimization_id]["progress"] = progress

    def set_result(self, optimization_id: str, result: OptimizationResult) -> None:
        """Set the final result for an optimization."""
        with self._store_lock:
            if optimization_id in self._optimizations:
                self._optimizations[optimization_id]["result"] = result

    def get_progress(self, optimization_id: str) -> Optional[OptimizationProgress]:
        """Get progress for an optimization."""
        with self._store_lock:
            opt = self._optimizations.get(optimization_id)
            return opt["progress"] if opt else None

    def get_result(self, optimization_id: str) -> Optional[OptimizationResult]:
        """Get result for an optimization."""
        with self._store_lock:
            opt = self._optimizations.get(optimization_id)
            return opt["result"] if opt else None

    def request_cancel(self, optimization_id: str) -> bool:
        """Request cancellation of an optimization."""
        with self._store_lock:
            if optimization_id in self._optimizations:
                self._optimizations[optimization_id]["cancel_requested"] = True
                return True
            return False

    def is_cancel_requested(self, optimization_id: str) -> bool:
        """Check if cancellation was requested."""
        with self._store_lock:
            opt = self._optimizations.get(optimization_id)
            return opt["cancel_requested"] if opt else False

    def cleanup(self, optimization_id: str) -> None:
        """Remove an optimization entry."""
        with self._store_lock:
            self._optimizations.pop(optimization_id, None)


# Global store instance
optimization_store = OptimizationStore()


class BaseOptimizer(ABC):
    """
    Abstract base class for parameter optimizers.

    Provides common functionality for progress tracking, cancellation,
    and result storage.
    """

    def __init__(self):
        self.optimization_id: Optional[str] = None
        self._start_time: float = 0
        self._cancelled = False
        self._store = optimization_store

    def _generate_id(self) -> str:
        """Generate a unique optimization ID."""
        return str(uuid.uuid4())[:8]

    def _update_progress(
        self,
        current_trial: int,
        total_trials: int,
        best_alpha: float,
        best_params: Dict[str, Any],
        message: str,
        status: OptimizationStatus = OptimizationStatus.RUNNING,
    ) -> None:
        """Update optimization progress."""
        if self.optimization_id is None:
            return

        elapsed = time.time() - self._start_time
        progress = OptimizationProgress(
            optimization_id=self.optimization_id,
            status=status,
            current_trial=current_trial,
            total_trials=total_trials,
            best_alpha=best_alpha,
            best_params=best_params,
            elapsed_seconds=elapsed,
            message=message,
        )
        self._store.update_progress(self.optimization_id, progress)

    def _check_cancelled(self) -> bool:
        """Check if optimization was cancelled."""
        if self.optimization_id:
            return self._store.is_cancel_requested(self.optimization_id)
        return self._cancelled

    def _finalize(self, result: OptimizationResult) -> None:
        """Store final result."""
        if self.optimization_id:
            self._store.set_result(self.optimization_id, result)

    @abstractmethod
    def optimize(self, **kwargs) -> OptimizationResult:
        """
        Run the optimization.

        Subclasses must implement this method to perform the actual optimization.
        """
        pass

    def start_async(self, **kwargs) -> str:
        """
        Start optimization asynchronously.

        Returns:
            optimization_id: Unique ID for tracking progress
        """
        self.optimization_id = self._generate_id()
        self._store.create(self.optimization_id, self.__class__.__name__)

        # Start in a separate thread
        thread = threading.Thread(
            target=self._run_optimization,
            kwargs=kwargs,
            daemon=True,
        )
        thread.start()

        return self.optimization_id

    def _run_optimization(self, **kwargs) -> None:
        """Run optimization with error handling."""
        self._start_time = time.time()

        try:
            # Initial progress
            self._update_progress(
                current_trial=0,
                total_trials=kwargs.get("max_trials", 100),
                best_alpha=float("-inf"),
                best_params={},
                message="Starting optimization...",
                status=OptimizationStatus.RUNNING,
            )

            result = self.optimize(**kwargs)
            self._finalize(result)

        except Exception as e:
            # Handle errors
            elapsed = time.time() - self._start_time
            result = OptimizationResult(
                success=False,
                best_params={},
                best_alpha=0.0,
                best_sharpe=0.0,
                best_total_return=0.0,
                best_max_drawdown=0.0,
                total_trials_evaluated=0,
                optimization_time_seconds=elapsed,
                error_message=str(e),
            )
            self._finalize(result)

            # Update progress with failed status
            self._update_progress(
                current_trial=0,
                total_trials=0,
                best_alpha=0.0,
                best_params={},
                message=f"Optimization failed: {str(e)}",
                status=OptimizationStatus.FAILED,
            )
