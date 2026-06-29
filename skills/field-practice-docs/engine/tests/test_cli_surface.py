from __future__ import annotations

from typer.testing import CliRunner

from field_practice.cli import app


def test_cli_help_when_rendered_then_exposes_three_public_commands_only() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("doctor", "draft", "document"):
        assert command in result.output
    for legacy_command in (
        "fill-cells",
        "run",
        "ingest-github",
        "ingest-calendar",
        "ingest-local-git",
        "validate",
        "enrich-weekly",
        "inspect-template",
        "fill-template",
        "export-hwpx",
    ):
        assert legacy_command not in result.output


def test_document_help_when_rendered_then_exposes_document_workflow_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["document", "--help"])

    assert result.exit_code == 0
    for command in (
        "cells",
        "inspect",
        "fill",
        "export",
        "blank",
        "render",
        "clean-pdf",
    ):
        assert command in result.output
