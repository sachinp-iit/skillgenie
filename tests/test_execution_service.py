"""
Tests for the execution service.
"""

from uuid import uuid4

import pytest

from skillgenie.constants import SkillStatus
from skillgenie.core.execution_service import ExecutionService
from skillgenie.exceptions import CapabilityNotFoundError


def _build(config, capability_repository, execution_repository, audit_repository, dummy_database):
    return ExecutionService(
        config=config,
        database=dummy_database,
        skill_repository=capability_repository,
        execution_repository=execution_repository,
        audit_repository=audit_repository,
    )


def _seed(repo, status=SkillStatus.PUBLISHED.value):
    capability_id = uuid4()

    repo.create(
        capability_id=capability_id,
        name="Web Scraper",
        description="Scrapes and extracts web content.",
        category="web",
        version="1.0.0",
        status=status,
    )

    return capability_id


def test_record_success_updates_metrics(
    config,
    capability_repository,
    execution_repository,
    audit_repository,
    dummy_database,
):
    service = _build(
        config,
        capability_repository,
        execution_repository,
        audit_repository,
        dummy_database,
    )

    capability_id = _seed(capability_repository)

    execution = service.record(
        capability_id=capability_id,
        task_name="scrape product page",
        execution_status="SUCCESS",
        execution_time_ms=125.0,
    )

    assert execution.task_name == "scrape product page"
    assert execution.execution_status.value == "SUCCESS"

    row = capability_repository.get_by_id(capability_id)

    assert row["usage_count"] == 1
    assert row["success_rate"] == 1.0
    assert row["avg_latency_ms"] == 125.0
    assert row["last_used_at"] is not None

    assert any(log["action"] == "EXECUTED" for log in audit_repository.logs)


def test_record_failure_drives_down_success_rate(
    config,
    capability_repository,
    execution_repository,
    audit_repository,
    dummy_database,
):
    service = _build(
        config,
        capability_repository,
        execution_repository,
        audit_repository,
        dummy_database,
    )

    capability_id = _seed(capability_repository)

    service.record(capability_id, "t1", "SUCCESS")
    service.record(capability_id, "t2", "FAILED", error_message="boom")

    row = capability_repository.get_by_id(capability_id)

    assert row["usage_count"] == 2
    assert row["success_rate"] == 0.5


def test_record_missing_skill_raises(
    config,
    capability_repository,
    execution_repository,
    audit_repository,
    dummy_database,
):
    service = _build(
        config,
        capability_repository,
        execution_repository,
        audit_repository,
        dummy_database,
    )

    with pytest.raises(CapabilityNotFoundError):
        service.record(
            capability_id=uuid4(),
            task_name="x",
            execution_status="SUCCESS",
        )