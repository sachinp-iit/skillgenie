# ============================================================================
# Project      : SkillGenie
# File         : constants.py
# Description  : Global constants used throughout the SkillGenie library.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from enum import Enum


class SkillStatus(str, Enum):
    """Capability lifecycle states."""

    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class SkillHealth(str, Enum):
    """Overall capability health."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    CRITICAL = "CRITICAL"


class RecommendationType(str, Enum):
    """Recommendation types."""

    EXACT = "EXACT"
    SIMILAR = "SIMILAR"
    RELATED = "RELATED"
    FALLBACK = "FALLBACK"


class ExecutionStatus(str, Enum):
    """Execution result."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


class LearningMode(str, Enum):
    """Learning strategies."""

    MANUAL = "MANUAL"
    ASSISTED = "ASSISTED"
    AUTOMATIC = "AUTOMATIC"


# JSONB Keys
RELATIONSHIP_GRAPH = "relationship_graph"
WORKFLOW = "workflow"
METADATA = "metadata"
CREATED_FROM = "created_from"


# Default thresholds
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_RECOMMENDATION_THRESHOLD = 0.80
DEFAULT_AUTO_APPROVAL_THRESHOLD = 0.95


# Embedding
DEFAULT_EMBEDDING_PROVIDER = "sentence-transformers"
DEFAULT_DISTANCE_METRIC = "cosine"


# Version
CURRENT_SCHEMA_VERSION = "1.0.0"