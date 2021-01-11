from nuke_from_orbit import cli
from nuke_from_orbit.commands import setup_commands, teardown_commands
from nuke_from_orbit.commands import update_config_commands, update_test_commands
from click.testing import CliRunner


def test_nuke():
    runner = CliRunner()
    result = runner.invoke(cli.nuke)
    assert result.exit_code == 0


def test_setup_config_file_only(mocker):
    mocker.patch("nuke_from_orbit.commands.setup_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.setup, ["--config-file", "test_config.yaml"])
    assert result.exit_code == 0
    setup_commands.main.assert_called_with(config_file="test_config.yaml", external=False, persistence=True)


def test_setup_no_persist(mocker):
    mocker.patch("nuke_from_orbit.commands.setup_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.setup, ["--config-file", "test_config.yaml", "--no-persistence"])
    assert result.exit_code == 0
    setup_commands.main.assert_called_with(config_file="test_config.yaml", external=False, persistence=False)


def test_setup_external(mocker):
    mocker.patch("nuke_from_orbit.commands.setup_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.setup, ["--config-file", "test_config.yaml", "--external"])
    assert result.exit_code == 0
    setup_commands.main.assert_called_with(config_file="test_config.yaml", external=True, persistence=True)


def test_setup_external_no_persistence(mocker):
    mocker.patch("nuke_from_orbit.commands.setup_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.setup, ["--config-file", "test_config.yaml", "--external", "--no-persistence"])
    assert result.exit_code == 0
    setup_commands.main.assert_called_with(config_file="test_config.yaml", external=True, persistence=False)


def test_teardown_no_all(mocker):
    mocker.patch("nuke_from_orbit.commands.teardown_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.teardown, ["--config-file", "test_config.yaml"])
    assert result.exit_code == 0
    teardown_commands.main.assert_called_with(config_file="test_config.yaml", all=False)


def test_teardown_all(mocker):
    mocker.patch("nuke_from_orbit.commands.teardown_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.teardown, ["--config-file", "test_config.yaml", "--all"])
    assert result.exit_code == 0
    teardown_commands.main.assert_called_with(config_file="test_config.yaml", all=True)


def test_update():
    runner = CliRunner()
    result = runner.invoke(cli.update)
    assert result.exit_code == 0


def test_update_config(mocker):
    mocker.patch("nuke_from_orbit.commands.update_config_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.config, ["--config-file", "test_config.yaml"])
    assert result.exit_code == 0
    update_config_commands.main.assert_called_with(config_file="test_config.yaml")


def test_update_test(mocker):
    mocker.patch("nuke_from_orbit.commands.update_test_commands.main")
    runner = CliRunner()
    result = runner.invoke(cli.test, ["--config-file", "test_config.yaml", "--tag", "v2"])
    assert result.exit_code == 0
    update_test_commands.main.assert_called_with(config_file="test_config.yaml", tag="v2")
