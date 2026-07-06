# ============================================================================
# Project      : SkillGenie
# File         : indexes.py
# Description  : Creates PostgreSQL indexes for optimal query performance.
#
# Usage:
#
#     from skillgenie.sql.indexes import create_indexes
#
#     create_indexes(database)
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager

def create_indexes(database: DatabaseManager) -> None:
    """
    Creates all indexes required by SkillGenie.
    """

    with database.engine.begin() as connection:

        # ---------------------------------------------------------------------
        # Vector Search Index (pgvector)
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_embedding
                ON skills
                USING hnsw (embedding vector_cosine_ops);
                """
            )
        )

        # ---------------------------------------------------------------------
        # JSONB Indexes
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_relationship_graph
                ON skills
                USING GIN (relationship_graph);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_workflow
                ON skills
                USING GIN (workflow);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_metadata
                ON skills
                USING GIN (metadata);
                """
            )
        )

        # ---------------------------------------------------------------------
        # B-Tree Indexes
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_name
                ON skills(name);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_category
                ON skills(category);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_status
                ON skills(status);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_confidence_score
                ON skills(confidence_score DESC);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_quality_score
                ON skills(quality_score DESC);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_success_rate
                ON skills(success_rate DESC);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_usage_count
                ON skills(usage_count DESC);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_skills_created_at
                ON skills(created_at DESC);
                """
            )
        )

        # ---------------------------------------------------------------------
        # Trace Indexes
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_traces_framework
                ON traces(agent_framework);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_traces_status
                ON traces(execution_status);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_traces_json
                ON traces
                USING GIN(trace);
                """
            )
        )

    print("Database indexes created successfully.")