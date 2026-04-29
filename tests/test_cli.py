from click.testing import CliRunner

from collection_swarm.cli import cli


def test_list_profiles_cli() -> None:
    result = CliRunner().invoke(cli, ["list-profiles"])

    assert result.exit_code == 0
    assert "Profiles" in result.output
    assert "cooperative" in result.output


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


def test_connection_cli_reports_missing_live_prerequisites() -> None:
    result = CliRunner().invoke(cli, ["test-connection", "--models", "cursor-auto,mistral-large-3-675b"])

    assert result.exit_code == 0
    assert "FAILED cursor-auto" in result.output
    assert "FAILED mistral-large-3-675b" in result.output
