# ============================================================================
# Project      : SkillGenie
# File         : bootstrap.py
# Description  : Initializes the SkillGenie database.
#
# Usage:
#
#     from skillgenie.config import Config
#     from skillgenie.database.bootstrap import bootstrap_database
#
#     config = Config()
#     bootstrap_database(config)
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.config import Config
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.sql.create_tables import create_tables
from skillgenie.database.sql.indexes import create_indexes


def bootstrap_database(config: Config) -> DatabaseManager:
    """
    Initialize SkillGenie database.

    Args:
        config: Configuration object.

    Returns:
        Initialized DatabaseManager.
    """

    # Create database manager
    database = DatabaseManager(config)

    # Verify database connectivity
    database.test_connection()

    # Create tables
    create_tables(database)

    # Create indexes
    create_indexes(database)

    return database