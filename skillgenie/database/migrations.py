# ============================================================================
# Project      : SkillGenie
# File         : migrations.py
# Description  : Executes all database migrations.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.sql.create_tables import create_tables
from skillgenie.database.sql.indexes import create_indexes


def migrate(database: DatabaseManager) -> None:
    """
    Execute all database migrations.

    Args:
        database: Database manager.
    """

    # Create tables
    create_tables(database)

    # Create indexes
    create_indexes(database)

    print("Database migration completed successfully.")