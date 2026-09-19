# ============================================================================
# Project      : SkillGenie
# File         : battle.py
# Description  : SkillGenie Arena — head-to-head skill battles with ELO rating.
#                Skills execute the same tasks, optionally under tool-failure
#                stress, and are scored on success rate, efficiency and
#                resilience.  A persistent leaderboard tracks ratings.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from skillgenie.arena.agent import ArenaAgent
from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class SkillGenieArena:
    """
    Run skill battles and maintain an ELO leaderboard.
    """

    INITIAL_RATING = 1200.0
    K_FACTOR = 32.0

    def __init__(
        self,
        config: Config,
        leaderboard_path: str | None = None,
    ):
        self._config = config
        self._leaderboard_path = leaderboard_path or self._config.get(
            "arena.leaderboard_path",
            "arena.leaderboard.json",
        )
        self._logger = Logger(config).log
        self._leaderboard: dict[str, dict[str, Any]] = self._load()

    def battle(
        self,
        *,
        skill_a: Any,
        skill_b: Any,
        task: str,
        rounds: int = 5,
        failure_rate: float = 0.30,
    ) -> dict[str, Any]:
        """
        Run a skill battle between two skills.
        """

        results: dict[str, dict[str, Any]] = {}
        matches: list[dict[str, Any]] = []

        wins = {self._key(skill_a): 0, self._key(skill_b): 0}
        losses = {self._key(skill_a): 0, self._key(skill_b): 0}
        draws = {self._key(skill_a): 0, self._key(skill_b): 0}

        for round_index in range(max(1, rounds)):
            seed = hash(f"{task}:{round_index}")

            agent_a = ArenaAgent(skill_a, seed=seed, failure_rate=failure_rate)
            agent_b = ArenaAgent(skill_b, seed=seed + 1, failure_rate=failure_rate)

            run_a = agent_a.run(task)
            run_b = agent_b.run(task)

            outcome_a = self._outcome_summary(run_a)
            outcome_b = self._outcome_summary(run_b)

            results.setdefault(
                self._key(skill_a),
                {"agent": skill_a.name, **outcome_a},
            )
            results.setdefault(
                self._key(skill_b),
                {"agent": skill_b.name, **outcome_b},
            )

            score_a = outcome_a["score"]
            score_b = outcome_b["score"]

            if score_a > score_b:
                wins[self._key(skill_a)] += 1
                losses[self._key(skill_b)] += 1
                match_winner = self._key(skill_a)
            elif score_b > score_a:
                wins[self._key(skill_b)] += 1
                losses[self._key(skill_a)] += 1
                match_winner = self._key(skill_b)
            else:
                draws[self._key(skill_a)] += 1
                draws[self._key(skill_b)] += 1
                match_winner = None

            matches.append(
                {
                    "round": round_index + 1,
                    "winner": match_winner,
                    "score": {"a": round(score_a, 4), "b": round(score_b, 4)},
                }
            )

        contenders = [
            {
                "id": key,
                "agent": results[key]["agent"],
                "wins": wins[key],
                "losses": losses[key],
                "draws": draws[key],
                "success_rate": results[key]["success_rate"],
                "efficiency": results[key]["efficiency"],
                "resilience": results[key]["resilience"],
            }
            for key in (self._key(skill_a), self._key(skill_b))
        ]

        total_a = wins[self._key(skill_a)] + losses[self._key(skill_a)] + draws[self._key(skill_a)]
        total_b = wins[self._key(skill_b)] + losses[self._key(skill_b)] + draws[self._key(skill_b)]

        if total_a > 0:
            contender_a = next(
                c for c in contenders
                if c["id"] == self._key(skill_a)
            )
            contender_a["accuracy"] = round(wins[self._key(skill_a)] / total_a, 3)

        if total_b > 0:
            contender_b = next(
                c for c in contenders
                if c["id"] == self._key(skill_b)
            )
            contender_b["accuracy"] = round(wins[self._key(skill_b)] / total_b, 3)

        if wins[self._key(skill_a)] > wins[self._key(skill_b)]:
            winner = self._key(skill_a)
        elif wins[self._key(skill_b)] > wins[self._key(skill_a)]:
            winner = self._key(skill_b)
        elif losses[self._key(skill_a)] < losses[self._key(skill_b)]:
            winner = self._key(skill_a)
        elif losses[self._key(skill_b)] < losses[self._key(skill_a)]:
            winner = self._key(skill_b)
        else:
            winner = None

        if winner is not None:
            winner_rating, loser_rating = self._update_elo(
                self._key(skill_a),
                self._key(skill_b),
                winner,
                skill_a.name,
                skill_b.name,
            )
        else:
            winner_rating = self._rating(self._key(skill_a))
            loser_rating = self._rating(self._key(skill_b))

            self._record(
                self._key(skill_a),
                winner_rating,
                skill_a.name,
                increment=False,
            )
            self._record(
                self._key(skill_b),
                loser_rating,
                skill_b.name,
                increment=False,
            )

        battle = {
            "task": task,
            "rounds": max(1, rounds),
            "failure_rate": failure_rate,
            "contenders": contenders,
            "winner": winner,
            "elo": {
                self._key(skill_a): round(winner_rating, 1),
                self._key(skill_b): round(loser_rating, 1),
            },
            "matches": matches,
        }

        self._logger.info(
            f"Arena battle complete. Winner: {winner or 'draw'}."
        )

        return battle

    def leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Top-rated skills by ELO.
        """

        entries = sorted(
            self._leaderboard.values(),
            key=lambda entry: entry["rating"],
            reverse=True,
        )

        return entries[: max(1, limit)]

    def exports(self) -> dict[str, Any]:
        """
        Serialized leaderboard snapshot.
        """

        return {
            "rating": self.INITIAL_RATING,
            "contenders": self.leaderboard(),
        }

    def _update_elo(
        self,
        key_a: str,
        key_b: str,
        winner: str,
        name_a: str,
        name_b: str,
    ) -> tuple[float, float]:
        """
        Update both ratings using a single K-factor ELO step.
        """

        rating_a = self._rating(key_a)
        rating_b = self._rating(key_b)

        expected_a = self._expected(rating_a, rating_b)
        expected_b = self._expected(rating_b, rating_a)

        if winner == key_a:
            new_a = rating_a + self.K_FACTOR * (1.0 - expected_a)
            new_b = rating_b + self.K_FACTOR * (0.0 - expected_b)
        else:
            new_a = rating_a + self.K_FACTOR * (0.0 - expected_a)
            new_b = rating_b + self.K_FACTOR * (1.0 - expected_b)

        self._record(key_a, new_a, name_a)
        self._record(key_b, new_b, name_b)

        return new_a, new_b

    def _rating(self, key: str) -> float:
        return float(self._leaderboard.get(key, {}).get("rating", self.INITIAL_RATING))

    @staticmethod
    def _expected(rating: float, opponent: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / 400.0))

    def _record(
        self,
        key: str,
        rating: float,
        name: str | None = None,
        increment: bool = True,
    ) -> None:
        entry = self._leaderboard.setdefault(
            key,
            {
                "skill_id": key,
                "name": name or key,
                "rating": self.INITIAL_RATING,
                "battles": 0,
            },
        )
        entry["rating"] = round(rating, 1)
        if name:
            entry["name"] = name
        if increment:
            entry["battles"] = int(entry.get("battles", 0)) + 1
        self._save()

    @staticmethod
    def _outcome_summary(run: dict[str, Any]) -> dict[str, Any]:
        """
        Turn a single run into success/efficiency/resilience scores.
        """

        success = 1.0 if run["success"] else 0.0

        step_count = max(1, run["step_count"])
        latency = max(1.0, run["total_latency_ms"])

        efficiency = 1.0 / (1.0 + (step_count * latency) / 10000.0)

        failed_steps = sum(
            1 for step in run["steps"] if step["status"] in {"FAILED", "RECOVERED"}
        )

        resilience = 1.0 - min(1.0, failed_steps / step_count)

        score = 0.60 * success + 0.20 * efficiency + 0.20 * resilience

        return {
            "success": bool(run["success"]),
            "success_rate": round(success, 3),
            "efficiency": round(efficiency, 3),
            "resilience": round(resilience, 3),
            "score": round(score, 4),
        }

    @staticmethod
    def _key(skill: Any) -> str:
        return str(getattr(skill, "id", ""))

    def _load(self) -> dict[str, Any]:
        try:
            path = Path(self._leaderboard_path)
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._logger.warning(
                f"Could not read arena leaderboard at "
                f"{self._leaderboard_path}."
            )

        return {}

    def _save(self) -> None:
        try:
            path = Path(self._leaderboard_path)
            if str(path.parent) != ".":
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._leaderboard, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            self._logger.warning(
                f"Could not persist arena leaderboard: {exc}"
            )