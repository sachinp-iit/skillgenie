"""
Tests for the command-line interface.
"""

import json
import tempfile
import os
from unittest.mock import MagicMock, patch

from skillgenie.cli.main import (
    build_parser,
    cmd_health,
    cmd_ingest,
    cmd_list,
    cmd_show,
    main,
)
from tests.conftest import make_capability


def test_parser_provides_expected_commands():
    parser = build_parser()

    subparsers = [
        action
        for action in parser._actions
        if action.dest == "command"
    ]

    assert subparsers

    available = set(subparsers[0].choices.keys())

    expected = {
        "init-db",
        "ingest",
        "learn",
        "learn-all",
        "relearn",
        "list",
        "show",
        "recommend",
        "approve",
        "reject",
        "publish",
        "deprecate",
        "archive",
        "restore",
        "exec",
        "health",
        "search",
        "api",
    }

    assert expected <= available


def test_parser_reject_reads_reason():
    parser = build_parser()

    args = parser.parse_args(["reject", "123", "why not"])

    assert args.reason == "why not"


def test_cmd_list_empty(monkeypatch):
    engine = MagicMock()

    engine.store.list.return_value = []

    monkeypatch.setattr("builtins.input", lambda _: "x")

    cmd_list(parser_args(), engine)


def test_cmd_list_prints_rows(capsys):
    engine = MagicMock()

    skill = make_capability()

    engine.store.list.return_value = [skill]

    cmd_list(parser_args(), engine)

    output = capsys.readouterr().out

    assert "Web Research" in output


def test_cmd_show_prints_json(capsys):
    engine = MagicMock()

    skill = make_capability()

    engine.store.get.return_value = skill

    args = parser_args(skill_id=str(skill.id))

    cmd_show(args, engine)

    payload = json.loads(capsys.readouterr().out)

    assert payload["name"] == "Web Research"


def test_cmd_ingest_from_file(tmp_path, capsys):
    engine = MagicMock()

    payload = {
        "task": "Scrape data",
        "steps": [],
        "metadata": {"category": "web"},
    }

    path = tmp_path / "trace.json"

    path.write_text(json.dumps(payload), encoding="utf-8")

    args = parser_args(file=str(path), name="Scrape data")

    cmd_ingest(args, engine)

    result = json.loads(capsys.readouterr().out)

    assert "trace_id" in result

    engine.traces.create.assert_called_once()


def test_cmd_health_prints_overview(capsys):
    engine = MagicMock()

    engine.health_overview.return_value = {
        "total_skills": 1,
        "statuses": {"PUBLISHED": 1},
        "health": {"GOOD": 1},
    }

    cmd_health(parser_args(), engine)

    output = capsys.readouterr().out

    assert '"total_skills": 1' in output


def test_main_list_with_mocked_engine(monkeypatch, capsys, tmp_path):
    engine = MagicMock()

    engine.store.list.return_value = []

    with patch(
        "skillgenie.cli.main._build_engine",
        return_value=engine,
    ):
        main(["--config", str(tmp_path / "config.json"), "list"])

    output = capsys.readouterr().out

    assert "No skills found." in output


def test_main_no_command_prints_help(capsys):
    with patch("skillgenie.cli.main._build_engine"):
        main(["--config", "x.json"])

    output = capsys.readouterr().out

    assert "usage" in output.lower() or "skillgenie" in output.lower()


def parser_args(**overrides):
    from types import SimpleNamespace

    args = SimpleNamespace(
        config="config/config.json",
        command="list",
        status=None,
        category=None,
        skill_id=None,
        file=None,
        name=None,
        framework="custom",
        query="",
        top=5,
        reason="",
    )

    for key, value in overrides.items():
        setattr(args, key, value)

    return args