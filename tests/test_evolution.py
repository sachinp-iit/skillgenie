"""
Tests for the evolution engine and version bumping.
"""

from datetime import datetime, timedelta

from skillgenie.constants import SkillStatus
from skillgenie.core.evolution import (
    SkillEvolutionEngine,
    bump_version,
)
from tests.conftest import make_capability, make_skill


def test_bump_version_patch():
    assert bump_version("1.2.3") == "1.2.4"
    assert bump_version("1.2.3", "patch") == "1.2.4"


def test_bump_version_minor():
    assert bump_version("1.2.3", "minor") == "1.3.0"


def test_bump_version_major():
    assert bump_version("1.2.3", "major") == "2.0.0"


def test_bump_version_short_and_invalid():
    assert bump_version("1.0") == "1.0.1"
    assert bump_version("not-a-version") == "not-a-version"


def _build_evolution(config, capability_repository, audit_repository, dummy_database, store):
    return SkillEvolutionEngine(
        config=config,
        database=dummy_database,
        store=store,
        skill_repository=capability_repository,
        audit_repository=audit_repository,
    )


def _seed(repo, status=SkillStatus.PUBLISHED, **overrides):
    row = make_skill(status=status.value, **overrides)

    repo.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    repo.update(capability_id=row["id"], **{k: v for k, v in row.items() if k not in {"id"}})

    return row["id"]


def test_evolve_bumps_version_and_reopens(
    config,
    capability_repository,
    audit_repository,
    dummy_database,
    store,
):
    skill_id = _seed(capability_repository, status=SkillStatus.PUBLISHED)

    evolution = _build_evolution(
        config,
        capability_repository,
        audit_repository,
        dummy_database,
        store,
    )

    skill = store.get(skill_id)

    updated = evolution.evolve(
        skill,
        changes={"description": "Updated description"},
        level="minor",
    )

    assert updated.version == "1.1.0"
    assert updated.description == "Updated description"

    refreshed = store.get(skill_id)

    assert refreshed.status == SkillStatus.CANDIDATE

    assert any(log["action"] == "EVOLVED" for log in audit_repository.logs)


def test_evolve_missing_skill_raises(config, capability_repository, audit_repository, dummy_database, store):
    from uuid import uuid4

    evolution = _build_evolution(
        config,
        capability_repository,
        audit_repository,
        dummy_database,
        store,
    )

    from skillgenie.models.capability import Capability

    phantom = Capability(name="ghost", description="nope", category="x")

    try:
        evolution.evolve(phantom, changes={})
    except Exception as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("Expected an exception for a missing skill.")


def test_deprecate_degraded(
    config,
    capability_repository,
    audit_repository,
    dummy_database,
    store,
):
    good_id = _seed(
        capability_repository,
        status=SkillStatus.PUBLISHED,
        success_rate=0.99,
    )
    bad_id = _seed(
        capability_repository,
        status=SkillStatus.PUBLISHED,
        success_rate=0.05,
        confidence_score=0.1,
        quality_score=0.1,
        avg_latency_ms=9000.0,
        name="sick skill",
    )

    evolution = _build_evolution(
        config,
        capability_repository,
        audit_repository,
        dummy_database,
        store,
    )

    deprecated = evolution.deprecate_degraded()

    assert bad_id in deprecated
    assert good_id not in deprecated

    assert store.get(bad_id).status == SkillStatus.DEPRECATED
    assert store.get(good_id).status == SkillStatus.PUBLISHED


def test_archive_stale(
    config,
    capability_repository,
    audit_repository,
    dummy_database,
    store,
):
    old = make_skill(
        status=SkillStatus.PUBLISHED.value,
        last_used_at=datetime.utcnow() - timedelta(days=400),
    )

    fresh = make_skill(
        status=SkillStatus.PUBLISHED.value,
        name="Fresh Skill",
        last_used_at=datetime.utcnow(),
    )

    old_id = old["id"]
    fresh_id = fresh["id"]

    capability_repository.create(
        capability_id=old_id,
        name=old["name"],
        description=old["description"],
        category=old["category"],
        version=old["version"],
        status=old["status"],
    )
    capability_repository.update(
        capability_id=old_id, **{k: v for k, v in old.items() if k != "id"}
    )

    capability_repository.create(
        capability_id=fresh_id,
        name=fresh["name"],
        description=fresh["description"],
        category=fresh["category"],
        version=fresh["version"],
        status=fresh["status"],
    )
    capability_repository.update(
        capability_id=fresh_id, **{k: v for k, v in fresh.items() if k != "id"}
    )

    evolution = _build_evolution(
        config,
        capability_repository,
        audit_repository,
        dummy_database,
        store,
    )

    archived = evolution.archive_stale(max_idle_days=90)

    assert old_id in archived
    assert fresh_id not in archived


def test_health_snapshot_counts(
    config,
    capability_repository,
    audit_repository,
    dummy_database,
    store,
):
    _seed(
        capability_repository,
        status=SkillStatus.PUBLISHED,
        success_rate=1.0,
        quality_score=1.0,
    )
    _seed(
        capability_repository,
        status=SkillStatus.PUBLISHED,
        success_rate=0.05,
        confidence_score=0.1,
        quality_score=0.1,
        avg_latency_ms=9000.0,
        name="sick",
    )

    evolution = _build_evolution(
        config,
        capability_repository,
        audit_repository,
        dummy_database,
        store,
    )

    snapshot = evolution.health_snapshot()

    assert snapshot["EXCELLENT"] >= 1
    assert snapshot["CRITICAL"] >= 1