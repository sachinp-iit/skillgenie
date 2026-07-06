# ============================================================================
# Project      : SkillGenie
# File         : exceptions.py
# Description  : Custom exceptions used throughout the SkillGenie library.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================


class SkillGenieError(Exception):
    """Base exception for SkillGenie."""


class ConfigurationError(SkillGenieError):
    """Raised when configuration is invalid."""


class DatabaseError(SkillGenieError):
    """Raised when a database operation fails."""


class CapabilityNotFoundError(SkillGenieError):
    """Raised when a capability cannot be found."""


class DuplicateCapabilityError(SkillGenieError):
    """Raised when attempting to create a duplicate capability."""


class ValidationError(SkillGenieError):
    """Raised when validation fails."""


class EmbeddingError(SkillGenieError):
    """Raised when embedding generation fails."""


class RecommendationError(SkillGenieError):
    """Raised when capability recommendation fails."""


class LearningError(SkillGenieError):
    """Raised when autonomous learning fails."""


class EvaluationError(SkillGenieError):
    """Raised when capability evaluation fails."""


class LifecycleError(SkillGenieError):
    """Raised when lifecycle transition is invalid."""