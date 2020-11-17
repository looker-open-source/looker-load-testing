import click
from nuke_from_orbit.commands import deploy, teardown, update


@click.group()
def nuke():
    pass


@nuke.command()
@click.option("--config", help="Which config file to use for the setup")
@click.option("--external", is_flag=True, help="Should external ingress be set up")
def setup(**kwargs):
    deploy.main(**kwargs)


@nuke.command()
@click.option("--config", help="Which config file to use for the setup")
def teardown(**kwargs):
    teardown.main(**kwargs)


@nuke.command()
@click.option("--config", help="Which config file to use for the setup")
def update(**kwargs):
    update.main(**kwargs)
