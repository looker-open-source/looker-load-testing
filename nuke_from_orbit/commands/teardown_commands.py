import os
import concurrent.futures
from nuke_from_orbit.utils import nuke_utils
from pathlib import Path


def main(**kwargs):
    root_dir = Path(__file__).parent.parent.parent
    config_dir = root_dir.joinpath("configs")
    sa_dir = root_dir.joinpath("credentials")

    config_file = config_dir.joinpath(kwargs["config_file"])

    # get the user credentials
    user_config = nuke_utils.set_variables(config_file)

    # determine if external has been triggered by testing for an ip address
    ip = nuke_utils.get_ip_address(user_config)

    # set gcp service account environment variable
    service_account_file = sa_dir.joinpath(user_config["gcp_service_account_file"]).resolve()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_file)

    # multithread the teardown
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        tasks = []
        tasks.append(executor.submit(nuke_utils.destroy_gke, user_config))
        if ip:
            tasks.append(executor.submit(nuke_utils.destroy_ip_address, user_config))

        for future in concurrent.futures.as_completed(tasks):
            future.result()

    print(f"{nuke_utils.BColors.OKGREEN}Teardown complete!{nuke_utils.BColors.ENDC}")
