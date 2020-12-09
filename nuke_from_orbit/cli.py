import click
from nuke_from_orbit.commands import setup_commands, teardown_commands
from nuke_from_orbit.commands import update_config_commands, update_test_commands


@click.group()
@click.version_option()
def nuke():
    pass


@nuke.command()
@click.option("--config-file", help="Which config file to use for the setup")
@click.option("--external", is_flag=True, help="Should external ingress be set up")
def setup(**kwargs):
    setup_commands.main(**kwargs)


@nuke.command()
@click.option("--config-file", help="Which config file to use for the setup")
def teardown(**kwargs):
    teardown_commands.main(**kwargs)


@nuke.group()
def update():
    pass


@update.command()
@click.option("--config-file", help="Which config file to use for the setup")
def config(**kwargs):
    update_config_commands.main(**kwargs)


@update.command()
@click.option("-t", "--tag", required=True, help="How to tag the container version")
@click.option("--config-file", help="Which config file to use for the setup")
def test(**kwargs):
    update_test_commands.main(**kwargs)
