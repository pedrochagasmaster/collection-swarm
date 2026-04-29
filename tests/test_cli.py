from click.testing import CliRunner

from collection_swarm.cli import cli


def test_list_profiles_cli() -> None:
    result = CliRunner().invoke(cli, ["list-profiles"])

    assert result.exit_code == 0
    assert "cooperative_hardship" in result.output


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
