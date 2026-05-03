from click.testing import CliRunner

from collection_swarm.cli import cli
from collection_swarm.models import EndedBy, Judgment, PaymentOutcome, SimulationResult
from collection_swarm.store import SimulationStore


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


def test_api_keys_cli_sets_lists_and_clears_dashboard_keys(tmp_path) -> None:
    db_path = tmp_path / "keys.sqlite"
    runner = CliRunner()

    set_result = runner.invoke(cli, ["--db", str(db_path), "api-keys", "set", "cursor", "--key", "sk-cursor-123456"])
    list_result = runner.invoke(cli, ["--db", str(db_path), "api-keys", "list"])
    clear_result = runner.invoke(cli, ["--db", str(db_path), "api-keys", "clear", "cursor"])

    assert set_result.exit_code == 0
    assert "Saved Cursor API key" in set_result.output
    assert list_result.exit_code == 0
    assert "Cursor" in list_result.output
    assert "************3456" in list_result.output
    assert "sk-cursor-123456" not in list_result.output
    assert clear_result.exit_code == 0
    assert "Cleared Cursor API key" in clear_result.output


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


def test_evolve_cli_runs_one_generation(tmp_path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "--db",
            str(tmp_path / "evolve.sqlite"),
            "evolve",
            "--generations",
            "1",
            "--tournament-rounds",
            "1",
            "--profiles",
            "cooperative_hardship",
            "--strategies",
            "empathetic_payment_plan",
            "--evolver-model",
            "local-scripted",
        ],
    )

    assert result.exit_code == 0
    assert "Evolution completed" in result.output


def test_calibrate_cli_evaluates_labels(tmp_path) -> None:
    db_path = tmp_path / "calibrate.sqlite"
    store = SimulationStore(db_path)
    store.save_run(
        SimulationResult(
            id="sim_label",
            profile_id="cooperative_hardship",
            strategy_id="empathetic_payment_plan",
            conversation_model="local-scripted",
            judge_model="local-judge",
            ended_by=EndedBy.COLLECTOR,
            judgment=Judgment(
                reasoning="stored",
                payment_outcome=PaymentOutcome.PAYMENT_PLAN,
                payment_probability=0.7,
                debtor_satisfaction=0.5,
                compliance_score=0.9,
                conversation_efficiency=2,
                rapport_built=0.5,
                escalation_risk=0.1,
            ),
        )
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        '[{"transcript_id":"sim_label","human_scores":{"payment_probability":0.8},"labeler_id":"analyst"}]',
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["--db", str(db_path), "calibrate", "--labels", str(labels)])

    assert result.exit_code == 0
    assert "Calibration labels: 1" in result.output
