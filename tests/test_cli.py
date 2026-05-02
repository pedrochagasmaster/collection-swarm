from click.testing import CliRunner

from collection_swarm.cli import cli


def test_list_profiles_cli() -> None:
    result = CliRunner().invoke(cli, ["list-profiles"])

    assert result.exit_code == 0
    assert "cooperative_hardship" in result.output
    assert "willbank_blocked_balance_hardship" in result.output


def test_simulate_cli_offline_no_save() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "simulate",
            "--profile",
            "cooperative_hardship",
            "--strategy",
            "empathetic_payment_plan",
            "--no-save",
        ],
    )

    assert result.exit_code == 0
    assert "Simulation" in result.output
    assert "Payment probability" in result.output


def test_serve_reload_reports_unsupported() -> None:
    result = CliRunner().invoke(cli, ["serve", "--reload"])

    assert result.exit_code != 0
    assert "--reload is not supported" in result.output


def test_model_report_cli_writes_markdown(tmp_path) -> None:
    output_path = tmp_path / "model-report.md"

    result = CliRunner().invoke(cli, ["model-report", "--output", str(output_path)])

    assert result.exit_code == 0
    assert "Wrote model-role report" in result.output
    assert "Cursor Model Role Evaluation" in output_path.read_text(encoding="utf-8")


def test_tournament_cli_swiss(tmp_path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "--db",
            str(tmp_path / "arena.sqlite"),
            "tournament",
            "--format",
            "swiss",
            "--rounds",
            "1",
            "--profiles",
            "cooperative_hardship,hostile_avoidant",
            "--strategies",
            "empathetic_payment_plan,neutral_reminder",
            "--conversation-model",
            "local-scripted",
            "--judge-model",
            "local-judge",
        ],
    )

    assert result.exit_code == 0
    assert "Tournament" in result.output
    assert "2 games" in result.output


def test_leaderboard_and_reset_elo_cli(tmp_path) -> None:
    db_path = tmp_path / "arena.sqlite"
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--db",
            str(db_path),
            "tournament",
            "--rounds",
            "1",
            "--profiles",
            "cooperative_hardship",
            "--strategies",
            "empathetic_payment_plan",
            "--conversation-model",
            "local-scripted",
            "--judge-model",
            "local-judge",
        ],
    )

    leaderboard = runner.invoke(cli, ["--db", str(db_path), "leaderboard"])
    reset = runner.invoke(cli, ["--db", str(db_path), "reset-elo"])
    empty = runner.invoke(cli, ["--db", str(db_path), "leaderboard"])

    assert leaderboard.exit_code == 0
    assert "empathetic_payment_plan" in leaderboard.output
    assert reset.exit_code == 0
    assert "Reset Elo ratings" in reset.output
    assert "No Elo ratings" in empty.output
