import os
from nuke_from_orbit.utils import nuke_utils
from pathlib import Path


def main(**kwargs):
    root_dir = Path(__file__).parent.parent.parent
    config_dir = root_dir.joinpath("configs")
    sa_dir = root_dir.joinpath("credentials")

    config_file = config_dir.joinpath(kwargs["config_file"])

    # get the user config
    user_config = nuke_utils.set_variables(config_file)

    # set gcp service account environment variable
    service_account_file = sa_dir.joinpath(user_config["gcp_service_account_file"]).resolve()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_file)

    # parse and render kubernetes template files
    file_list = nuke_utils.collect_kube_yaml_templates()
    nuke_utils.render_kubernetes_templates(user_config, file_list)

    # set kubernetes context
    nuke_utils.set_kubernetes_context(user_config)

    # deploy secrets
    nuke_utils.deploy_looker_secret(user_config)

    # deploy locust
    nuke_utils.deploy_locust(cycle=True)

    print(f"{nuke_utils.BColors.OKGREEN}Update complete!{nuke_utils.BColors.ENDC}")
