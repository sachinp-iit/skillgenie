"""
Tests for the SkillGenie Arena (head-to-head battles + ELO).
"""

from skillgenie.arena import SkillGenieArena
from skillgenie.arena.agent import ArenaAgent
from tests.conftest import make_capability


def _robust_skill(name="Robust Skill"):
    return make_capability(
        name=name,
        description="A skill with fallback tooling for resilience.",
        category="general",
        status="PUBLISHED",
        workflow={
            "name": name,
            "framework": "custom",
            "steps": [
                {
                    "order": 1,
                    "name": "fetch",
                    "tool": "web_search",
                    "output": {"result": "pages"},
                },
                {
                    "order": 2,
                    "name": "summarize",
                    "tool": "summarize",
                    "output": {"result": "notes"},
                },
            ],
        },
        metadata={
            "tools": [
                {"name": "web_search", "type": "web", "fallback": True},
                {"name": "summarize", "type": "llm", "fallback": True},
            ],
            "search_profile": {"tokens": "robust skill fetch summarize"},
        },
    )


def _fragile_skill(name="Fragile Skill"):
    return make_capability(
        name=name,
        description="A skill with no fallback tooling.",
        category="general",
        status="PUBLISHED",
        workflow={
            "name": name,
            "framework": "custom",
            "steps": [
                {
                    "order": 1,
                    "name": "fetch",
                    "tool": "web_search",
                    "output": {"result": "pages"},
                },
                {
                    "order": 2,
                    "name": "summarize",
                    "tool": "summarize",
                    "output": {"result": "notes"},
                },
            ],
        },
        metadata={
            "tools": [
                {"name": "web_search", "type": "web"},
                {"name": "summarize", "type": "llm"},
            ],
            "search_profile": {"tokens": "fragile skill fetch summarize"},
        },
    )


def test_agent_run_reports_success_and_steps():
    agent = ArenaAgent(_robust_skill(), seed=1, failure_rate=0.0)

    run = agent.run("research a topic")

    assert run["success"] is True
    assert run["step_count"] == 2
    assert all(step["status"] == "OK" for step in run["steps"])


def test_fragile_skill_fails_under_failure_injection():
    robust = ArenaAgent(_robust_skill(), seed=7, failure_rate=1.0)
    fragile = ArenaAgent(_fragile_skill(), seed=7, failure_rate=1.0)

    robust_run = robust.run("research a topic")
    fragile_run = fragile.run("research a topic")

    assert robust_run["success"] is True
    assert fragile_run["success"] is False


def test_battle_produces_winner_and_contenders(config, tmp_path):
    arena = SkillGenieArena(
        config=config,
        leaderboard_path=str(tmp_path / "arena.json"),
    )

    battle = arena.battle(
        skill_a=_robust_skill(),
        skill_b=_fragile_skill(),
        task="research a topic",
        rounds=5,
        failure_rate=0.50,
    )

    assert battle["rounds"] == 5
    assert len(battle["contenders"]) == 2
    assert battle["winner"] is not None

    robust = next(
        contender
        for contender in battle["contenders"]
        if contender["agent"].startswith("Robust")
    )
    assert robust["wins"] >= robust["losses"]


def test_elo_updates_and_leaderboard(config, tmp_path):
    arena = SkillGenieArena(
        config=config,
        leaderboard_path=str(tmp_path / "arena.json"),
    )

    strong = _robust_skill("Strong")
    weak = _fragile_skill("Weak")

    for _ in range(3):
        arena.battle(
            skill_a=strong,
            skill_b=weak,
            task="research a topic",
            rounds=3,
            failure_rate=0.5,
        )

    board = arena.leaderboard()

    assert len(board) == 2

    strong_entry = next(entry for entry in board if entry["name"] == "Strong")
    weak_entry = next(entry for entry in board if entry["name"] == "Weak")

    assert strong_entry["rating"] > weak_entry["rating"]
    assert strong_entry["battles"] > 0


def test_leaderboard_persists(config, tmp_path):
    path = tmp_path / "arena.json"

    arena = SkillGenieArena(config=config, leaderboard_path=str(path))

    arena.battle(
        skill_a=_robust_skill("Persister"),
        skill_b=_fragile_skill("Rebooter"),
        task="research a topic",
        rounds=2,
        failure_rate=0.5,
    )

    reloaded = SkillGenieArena(config=config, leaderboard_path=str(path))

    assert reloaded.leaderboard()