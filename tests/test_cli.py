from click.testing import CliRunner

from collection_swarm.cli import cli


def test_list_profiles_cli() -> None:
    result = CliRunner().invoke(cli, ["list-profiles"])

    assert result.exit_code == 0
    assert "Profiles" in result.output
    assert "willbank_credit_ca" in result.output


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
