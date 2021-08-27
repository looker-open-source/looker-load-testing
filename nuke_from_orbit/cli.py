import click
from nuke_from_orbit.commands import setup_commands, teardown_commands
from nuke_from_orbit.commands import update_config_commands, update_test_commands


@click.group()
@click.version_option()
def nfo():
    pass


@nfo.command()
@click.option("--config-file", help="Which config file to use for the setup", required=True)
@click.option("--external", is_flag=True, help="Should external ingress be set up")
@click.option("--persistence/--no-persistence", default=True, help="Should persistent disk setup be skipped?")
def setup(**kwargs):
    setup_commands.main(**kwargs)


@nfo.command()
@click.option("--config-file", help="Which config file to use for the setup", required=True)
@click.option("--all", is_flag=True, help="Should teardown include persistent disk")
def teardown(**kwargs):
    teardown_commands.main(**kwargs)


@nfo.group()
def update():
    pass


@update.command()
@click.option("--config-file", help="Which config file to use for the setup", required=True)
def config(**kwargs):
    update_config_commands.main(**kwargs)


@update.command()
@click.option("-t", "--tag", required=True, help="How to tag the container version")
@click.option("--config-file", help="Which config file to use for the setup", required=True)
def test(**kwargs):
    update_test_commands.main(**kwargs)
