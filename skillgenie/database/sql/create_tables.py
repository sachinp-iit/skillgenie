# ============================================================================
# Project      : SkillGenie
# File         : create_tables.py
# Description  : Creates all PostgreSQL database objects required by
#                SkillGenie.
#
# Usage:
#
#     from skillgenie.sql.create_tables import create_tables
#
#     create_tables(database)
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager


def create_tables(database: DatabaseManager) -> None:
    """
    Creates all SkillGenie database tables.
    """

    with database.engine.begin() as connection:

        # ---------------------------------------------------------------------
        # Enable pgvector extension
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE EXTENSION IF NOT EXISTS vector;
                """
            )
        )

        # ---------------------------------------------------------------------
        # Skills / Capabilities
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS skills (

                    id UUID PRIMARY KEY,

                    name VARCHAR(255) NOT NULL,

                    description TEXT,

                    category VARCHAR(100),

                    version VARCHAR(20),

                    status VARCHAR(30),

                    confidence_score DOUBLE PRECISION DEFAULT 0,

                    quality_score DOUBLE PRECISION DEFAULT 0,

                    success_rate DOUBLE PRECISION DEFAULT 0,

                    usage_count INTEGER DEFAULT 0,

                    avg_latency_ms DOUBLE PRECISION DEFAULT 0,

                    embedding VECTOR(1024),

                    relationship_graph JSONB,

                    workflow JSONB,

                    metadata JSONB,

                    created_from JSONB,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    last_used_at TIMESTAMP

                );
                """
            )
        )

        # ---------------------------------------------------------------------
        # Execution Traces
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS traces (

                    id UUID PRIMARY KEY,

                    trace_name VARCHAR(255),

                    agent_framework VARCHAR(100),

                    task_description TEXT,

                    execution_status VARCHAR(30),

                    execution_time_ms DOUBLE PRECISION,

                    trace JSONB,

                    metadata JSONB,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

                );
                """
            )
        )

        # ---------------------------------------------------------------------
        # Capability Metrics
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS capability_metrics (

                    id UUID PRIMARY KEY,

                    capability_id UUID
                        REFERENCES skills(id)
                        ON DELETE CASCADE,

                    confidence_score DOUBLE PRECISION,

                    quality_score DOUBLE PRECISION,

                    success_rate DOUBLE PRECISION,

                    avg_latency_ms DOUBLE PRECISION,

                    usage_count INTEGER,

                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

                );
                """
            )
        )

        # ---------------------------------------------------------------------
        # Audit Logs
        # ---------------------------------------------------------------------

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (

                    id UUID PRIMARY KEY,

                    capability_id UUID,

                    action VARCHAR(100),

                    performed_by VARCHAR(255),

                    remarks TEXT,

                    payload JSONB,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

                );
                """
            )
        )

    print("SkillGenie database schema created successfully.")