import os
import concurrent.futures
from nuke_from_orbit.utils import nuke_utils
from pathlib import Path


def main(**kwargs):
    root_dir = Path(__file__).parent.parent.parent
    config_dir = root_dir.joinpath("configs")
    sa_dir = root_dir.joinpath("credentials")

    # set the external boolean
    external = kwargs["external"]

    # setting tag to v1 for initial setup
    tag = "v1"

    config_file = config_dir.joinpath(kwargs["config_file"])

    # get the user credentials
    user_config = nuke_utils.set_variables(config_file, tag, external)

    # set gcp service account environment variable
    service_account_file = sa_dir.joinpath(user_config["gcp_service_account_file"]).resolve()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_file)

    # multithread the gke deployment and cloud build for maximum fast
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        tasks = []
        tasks.append(executor.submit(nuke_utils.deploy_gke, user_config))
        tasks.append(executor.submit(nuke_utils.deploy_test_container_image, user_config))
        if external:
            tasks.append(executor.submit(nuke_utils.deploy_ip_address, user_config))

        for future in concurrent.futures.as_completed(tasks):
            future.result()

    # fetch the ip address for final output
    ip = nuke_utils.get_ip_address(user_config)
    dns = user_config["loadtest_dns_domain"]

    # parse and render kubernetes template files
    file_list = nuke_utils.collect_kube_yaml_templates(external)
    nuke_utils.render_kubernetes_templates(user_config, file_list)

    # deploy secrets
    nuke_utils.deploy_looker_secret(user_config)
    if external:
        nuke_utils.deploy_oauth_secret(user_config)

    # deploy external components if required
    if external:
        nuke_utils.deploy_external()

    # deploy locust
    nuke_utils.deploy_locust()

    # deploy secondary services
    nuke_utils.deploy_secondary()

    ip_message = f"Cluster IP is {ip}. Please create an A Record in your DNS provider for *.{dns} that points to {ip}."
    kubectl_message = (
        "To configure kubectl access please run the following command:\n"
        f"{nuke_utils.kubeconfig_env_variable_command()}\n\n"
    )
    port_forward_message = (
        "You can now use `kubectl port-forward` commands."
        "This will allow you to access your load test services directly. Read more here:\n"
        "https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster\n\n"
        "All services are available on port 80. Find services with `kubectl get svc`. Then forward to a desired port.\n"
        "(e.g. `kubectl port-forward service/lm-pod 8089:80` forwards locust master to your localhost port 8089)."
    )

    print(f"{nuke_utils.BColors.OKGREEN}Setup complete!{nuke_utils.BColors.ENDC}")
    print(f"{nuke_utils.BColors.OKGREEN}{kubectl_message}{nuke_utils.BColors.ENDC}")
    if external:
        print(f"{nuke_utils.BColors.OKGREEN}{ip_message}{nuke_utils.BColors.ENDC}")
    print(f"{nuke_utils.BColors.OKGREEN}{port_forward_message}{nuke_utils.BColors.ENDC}")
