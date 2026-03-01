"""Factory for creating regime detection models."""

from typing import List, Optional
import warnings

from .base_detector import BaseRegimeDetector, ModelConfig, ModelType
from .hmm_model import HMMRegimeDetector
from .hmm_student_t import StudentTRegimeDetector

# Check for optional dependencies
try:
    from .rs_garch import RSGARCHDetector, ARCH_AVAILABLE
except ImportError:
    ARCH_AVAILABLE = False
    RSGARCHDetector = None

try:
    from .bayesian_hmm import BayesianHMMDetector, POMEGRANATE_AVAILABLE
except ImportError:
    POMEGRANATE_AVAILABLE = False
    BayesianHMMDetector = None


class ModelFactory:
    """
    Factory for creating regime detection models.

    Provides a unified interface for creating different model types
    and checking which models are available based on installed packages.
    """

    @staticmethod
    def create(model_type: ModelType, config: Optional[ModelConfig] = None) -> BaseRegimeDetector:
        """
        Create a regime detection model.

        Args:
            model_type: Type of model to create
            config: Model configuration

        Returns:
            Configured model instance

        Raises:
            ValueError: If model type is unknown or unavailable
        """
        if config is None:
            config = ModelConfig()

        if model_type == ModelType.HMM_GAUSSIAN:
            return HMMRegimeDetector(config=config)

        elif model_type == ModelType.HMM_STUDENT_T:
            return StudentTRegimeDetector(
                config=config,
                df=config.student_t_df,
            )

        elif model_type == ModelType.RS_GARCH:
            if not ARCH_AVAILABLE or RSGARCHDetector is None:
                raise ValueError(
                    "RS-GARCH model requires the 'arch' package. "
                    "Install with: pip install arch>=6.2.0"
                )
            return RSGARCHDetector(config=config)

        elif model_type == ModelType.BAYESIAN_HMM:
            if BayesianHMMDetector is None:
                raise ValueError(
                    "Bayesian HMM requires the 'pomegranate' package. "
                    "Install with: pip install pomegranate>=1.0.0"
                )
            return BayesianHMMDetector(config=config)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

    @staticmethod
    def create_from_string(
        model_type_str: str,
        config: Optional[ModelConfig] = None
    ) -> BaseRegimeDetector:
        """
        Create a model from a string type name.

        Args:
            model_type_str: String representation of model type
            config: Model configuration

        Returns:
            Configured model instance
        """
        try:
            model_type = ModelType(model_type_str)
        except ValueError:
            raise ValueError(
                f"Unknown model type: {model_type_str}. "
                f"Available types: {[t.value for t in ModelFactory.available_models()]}"
            )

        return ModelFactory.create(model_type, config)

    @staticmethod
    def available_models() -> List[ModelType]:
        """
        Get list of available model types.

        Checks which optional dependencies are installed
        and returns only the models that can be used.

        Returns:
            List of available ModelType values
        """
        available = [
            ModelType.HMM_GAUSSIAN,
            ModelType.HMM_STUDENT_T,  # Custom implementation, always available
        ]

        if ARCH_AVAILABLE and RSGARCHDetector is not None:
            available.append(ModelType.RS_GARCH)

        if BayesianHMMDetector is not None:
            # Bayesian HMM has a fallback, so it's always "available"
            available.append(ModelType.BAYESIAN_HMM)

        return available

    @staticmethod
    def is_available(model_type: ModelType) -> bool:
        """
        Check if a specific model type is available.

        Args:
            model_type: Model type to check

        Returns:
            True if the model can be created
        """
        return model_type in ModelFactory.available_models()

    @staticmethod
    def get_model_info(model_type: ModelType) -> dict:
        """
        Get information about a model type.

        Args:
            model_type: Model type to get info for

        Returns:
            Dictionary with model name, description, and requirements
        """
        info = {
            ModelType.HMM_GAUSSIAN: {
                "name": "HMM (Gaussian)",
                "description": "Standard Hidden Markov Model with Gaussian emissions",
                "requirements": "hmmlearn (included)",
                "available": True,
            },
            ModelType.HMM_STUDENT_T: {
                "name": "HMM (Student-t)",
                "description": "HMM with Student-t emissions for heavy tails",
                "requirements": "scipy (included)",
                "available": True,
            },
            ModelType.RS_GARCH: {
                "name": "RS-GARCH",
                "description": "Regime-Switching GARCH for volatility clustering",
                "requirements": "arch>=6.2.0",
                "available": ARCH_AVAILABLE,
            },
            ModelType.BAYESIAN_HMM: {
                "name": "Bayesian HMM",
                "description": "Bayesian HMM with uncertainty quantification",
                "requirements": "pomegranate>=1.0.0 (optional, has fallback)",
                "available": True,  # Has fallback
            },
        }

        return info.get(model_type, {
            "name": str(model_type),
            "description": "Unknown model type",
            "requirements": "Unknown",
            "available": False,
        })

    @staticmethod
    def get_all_model_info() -> List[dict]:
        """
        Get information about all model types.

        Returns:
            List of dictionaries with model information
        """
        return [
            {**ModelFactory.get_model_info(mt), "type": mt.value}
            for mt in ModelType
        ]
