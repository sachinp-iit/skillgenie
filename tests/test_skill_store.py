"""
Tests for the skill store.
"""

from uuid import uuid4

import pytest

from skillgenie.constants import SkillHealth, SkillStatus
from tests.conftest import make_capability, make_skill


def test_create_roundtrip(store, capability_repository):
    skill = make_capability()

    store.create(skill)

    fetched = store.get(skill.id)

    assert fetched is not None
    assert fetched.name == skill.name
    assert fetched.category == skill.category
    assert fetched.version == "1.0.0"
    assert fetched.status == SkillStatus.DRAFT
    assert fetched.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]


def test_create_requires_fields(store):
    from skillgenie.models.capability import Capability

    with pytest.raises(Exception):
        Capability()


def test_get_missing_returns_none(store):
    assert store.get(uuid4()) is None


def test_list_filters_by_status(store, capability_repository):
    published = make_skill(status=SkillStatus.PUBLISHED.value, name="Published Sk")
    draft = make_skill(status=SkillStatus.DRAFT.value, name="Draft Skill")

    for row in (published, draft):
        capability_repository.create(
            capability_id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            version=row["version"],
            status=row["status"],
        )
        capability_repository.update(
            capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"}
        )

    skills = store.list(status=SkillStatus.PUBLISHED.value)

    assert len(skills) == 1
    assert skills[0].name == "Published Sk"

    all_skills = store.list()

    assert len(all_skills) == 2


def test_list_filters_by_category(store, capability_repository):
    row = make_skill(category="finance", name="Billing Skill")

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    assert len(store.list(category="finance")) == 1
    assert len(store.list(category="research")) == 0


def test_update_normalizes_enum_fields(store, capability_repository):
    skill = make_capability()

    store.create(skill)

    updated = store.update(
        skill.id,
        status=SkillStatus.PUBLISHED.value,
        health="EXCELLENT",
    )

    assert updated is not None
    assert updated.status == SkillStatus.PUBLISHED
    assert updated.health == SkillHealth.EXCELLENT


def test_update_unknown_field_raises(store):
    skill = make_capability()

    store.create(skill)

    with pytest.raises(ValueError):
        store.update(skill.id, does_not_exist=True)


def test_update_missing_skill_returns_none(store):
    from skillgenie.exceptions import CapabilityNotFoundError

    with pytest.raises(CapabilityNotFoundError):
        store.update(uuid4(), name="x")


def test_delete(store, capability_repository):
    skill = make_capability()

    store.create(skill)

    store.delete(skill.id)

    assert store.get(skill.id) is None


def test_lexical_search_without_embedding(store, capability_repository):
    row = make_skill(name="Web Research", description="search the web and cite sources")

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )
    capability_repository.update(
        capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"}
    )

    results = store.search(
        "search the web",
        top_k=5,
        threshold=0.0,
        status=SkillStatus.DRAFT.value,
    )

    assert results

    assert str(results[0]["skill"].id) == str(row["id"])

    assert results[0]["type"] in {
        "EXACT",
        "SIMILAR",
        "RELATED",
        "FALLBACK",
    }


def test_search_respects_status_filter(store, capability_repository):
    row = make_skill(
        status=SkillStatus.PUBLISHED.value,
        name="Published Only",
        description="unique phrase tangent",
    )

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )
    capability_repository.update(
        capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"}
    )

    results = store.search(
        "unique phrase tangent",
        threshold=0.0,
        status=SkillStatus.CANDIDATE.value,
    )

    assert results == []