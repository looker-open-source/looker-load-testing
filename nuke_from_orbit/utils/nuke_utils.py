import os
import yaml
import subprocess
import shutil
from googleapiclient.errors import HttpError
from pathlib import Path
from jinja2 import Template
from nuke_from_orbit.utils import gke_cluster, cloud_build, kubernetes_deploy
from time import sleep

SCRIPT_PATH = Path(__file__).parent
APPLY_COMMAND = ["kubectl", "apply", "-f"]


class BColors:
    """Convenience class for adding colors  to output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class MissingRequiredArgsError(Exception):
    """Exception raised if user config is missing any required arguments"""
    def __init__(self, missing_args, message="Missing required args! Missing args:"):
        self.missing_args = missing_args
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} {self.missing_args}"


class TooManyWorkersError(Exception):
    """Exception raised if too many workers are requested for the underlying infrastrucure
    to handle.
    """
    def __init__(self, requested_workers, max_workers, message="Cluster worker capacity exceeded!"):
        self.requested_workers = requested_workers
        self.max_workers = max_workers
        self.message = f"{message} Requested: {self.requested_workers}. Capacity: {self.max_workers}"
        super().__init__(self.message)

    def __str__(self):
        return f"{BColors.FAIL}{self.message}{BColors.ENDC}"


class TagMatchError(Exception):
    """Exception raised if the provided update tag matches the existing tag."""

    def __init__(self, tag, message="Provided tag already in use!"):
        self.tag = tag
        self.message = f"{message} Tag: {tag}"
        super().__init__(self.message)

    def __str__(self):
        return f"{BColors.FAIL}{self.message}{BColors.ENDC}"


def check_required_args(user_config, external=False):
    """Checks a user config dict against required args and throws an error if any are missing.
    Returns a 1 if all required args are present.
    """

    # parse required args
    config_args_path = SCRIPT_PATH.joinpath("rendered", "config_args.yaml")
    with open(config_args_path) as f:
        config_args = yaml.safe_load(f)

    # validate user config against required args
    required_args = config_args["required_args"]
    if external:
        required_args.extend(config_args["required_external_args"])

    missing_args = set(required_args) - set(user_config)

    if missing_args:
        raise MissingRequiredArgsError(missing_args)

    # warn if any optional args are missing
    optional_args = config_args["optional_args"]
    missing_optional_args = set(optional_args) - set(user_config)
    if missing_optional_args:
        message = "Note - some optional arguments missing. This is probably fine, but you may want to double check!"
        print(f"{BColors.WARNING}{message} Missing args: {missing_optional_args}{BColors.ENDC}")

    return 1


def check_worker_count(user_config):
    """Accepts a dict of user configs and confirms if the worker count is valid. If
    the specified number of workers exceeds what the cluster can handle an exception
    is thrown. Returns a 1 if worker count is acceptable.
    """

    cores = int(user_config["gcp_cluster_machine_type"].split("-")[-1])
    node_count = int(user_config["gcp_cluster_node_count"])
    requested_workers = int(user_config["loadtest_worker_count"])

    # Leave 2 cores for master and secondary service overhead
    max_workers = (cores * node_count) - 2

    if requested_workers > max_workers:
        raise TooManyWorkersError(requested_workers, max_workers)

    return 1


def set_variables(config_file, image_tag="v1", external=False):
    """Reads the user config file and checks for required args. Image tag is then added.
    Config must be in yaml format. Returns the parsed config options.
    """

    # parse and flatten user config
    with open(config_file) as f:
        user_config = yaml.safe_load(f)

    flat_user_config = {}
    for k, v in user_config.items():
        flat_user_config = {**flat_user_config, **v}

    # check required args
    check_required_args(flat_user_config, external)

    # check worker count
    check_worker_count(flat_user_config)

    # update config values to include image tag
    flat_user_config["image_tag"] = image_tag

    return flat_user_config


def copy_test_script_to_docker(test_script):
    """Accepts a file name (assumed to be in the root test_scripts directory) and copies/renames it
    into the appropriate directory for the docker image to build.
    """

    test_script_path = SCRIPT_PATH.parent.parent.joinpath("locust_test_scripts", test_script)
    target_path = SCRIPT_PATH.parent.joinpath("docker-image", "locust-tasks", "tasks.py")

    shutil.copy(test_script_path, target_path)


def collect_kube_yaml_templates(external=False):
    """Assembles and returns the appropriate list of template kubernetes yamls
    for rendering. Returns the list of files.
    """

    template_path = SCRIPT_PATH.joinpath("templates")

    external_yamls = [
        template_path.joinpath("loadtest-cert.yaml"),
        template_path.joinpath("loadtest-ingress.yaml"),
        template_path.joinpath("config-default.yaml")
    ]

    yamls = [
        template_path.joinpath("locust-controller.yaml"),
        template_path.joinpath("locust-worker-controller.yaml"),
        template_path.joinpath("prometheus-config.yaml"),
        template_path.joinpath("prometheus-controller.yaml"),
        template_path.joinpath("grafana-config.yaml"),
        template_path.joinpath("grafana-controller.yaml")
    ]

    # external first, if required... order matters a little
    if external:
        file_list = external_yamls + yamls
    else:
        file_list = yamls

    return file_list


def render_kubernetes_templates(values_dict, files):
    """Accepts a dict of user config values and a list of files and then renders those
    files and writes them to the `rendered` directory.
    """

    for file in files:
        print(f"Rendering {file}")
        dest_file = SCRIPT_PATH.joinpath("rendered", file.name)
        template = file.read_text()
        rendered = Template(template).render(**values_dict)

        with open(dest_file, "w") as f:
            f.write(rendered)


def deploy_persistant_disk(user_config):
    """Accepts a dict of validated user configs and uses them to build a GCE persistant disk.
    First we check to see if the disk currently exists (i.e. persisted from last session) If
    the disk does not exist it is created. This disk will be used as a persistant volume for
    prometheus to retain data.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    zone = user_config["gcp_zone"]

    # create the compute client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_compute_client()

    try:
        gke_cluster.fetch_zonal_disk(name, project, zone, client)
        print(f"Found persistant disk {name}. Attaching to cluster...")
    except HttpError:
        print("No existing persistant disk found. Creating...")
        disk_task = gke_cluster.create_zonal_disk(name, project, zone, client)

        running = True
        while running:
            status = gke_cluster.compute_zonal_task_status(disk_task, project, zone, client)
            print(f"Creating persistant disk {name}: {status}")
            if status == "DONE":
                running = False
            else:
                sleep(2)


def destroy_persistant_disk(user_config):
    """Accepts a dict of validated user configs and uses them to destroy a GCE persistant disk.
    Tracks the status of the job and confirms successful deletion.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    zone = user_config["gcp_zone"]

    # create the compute client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_compute_client()

    try:
        gke_cluster.fetch_zonal_disk(name, project, zone, client)
        print(f"Found persistant disk {name}. Deleting...")
        disk_task = gke_cluster.delete_zonal_disk(name, project, zone, client)

        running = True
        while running:
            status = gke_cluster.compute_zonal_task_status(disk_task, project, zone, client)
            print(f"Deleting persistant disk {name}: {status}")
            if status == "DONE":
                running = False
            else:
                sleep(2)
    except HttpError:
        print("No persistant disk exists. Moving on!")


def deploy_ip_address(user_config):
    """Accepts a dict of validated user configs and uses them to deploy a global ip
    address that is used for the gke ingress controller (if appropriate).
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]

    # create the compute client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_compute_client()

    address_task = gke_cluster.create_global_ip(name, project, client)

    running = True
    while running:
        status = gke_cluster.compute_task_status(address_task, project, client)
        print(f"Global IP Address {name}: {status}")
        if status == "DONE":
            running = False
        else:
            sleep(2)


def get_ip_address(user_config):
    """Accepts a dict of validated user configs and uses them to attempt a get
    of the specified global ip address. If successful, returns the ip address as
    a string. If an exception is thrown it will return False.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]

    # create the compute client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_compute_client()

    try:
        ip = gke_cluster.fetch_ip_address(name, project, client)
        return ip
    except HttpError:
        return False


def destroy_ip_address(user_config):
    """Accepts a dict of validated user configs and uses them to destroy a global
    ip address. Tracks the status of the job and confirms successful deletion.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]

    # create the compute client. we're relying on the environment to be set for credentials
    client = gke_cluster.get_compute_client()

    address_delete_task = gke_cluster.delete_global_ip(name, project, client)

    running = True
    while running:
        status = gke_cluster.compute_task_status(address_delete_task, project, client)
        print(f"Delete Global IP Address {name}: {status}")
        if status == "DONE":
            running = False
        else:
            sleep(2)


def deploy_gke(user_config):
    """Accepts a dict of validated user configs and uses them to configure and deploy
    a GKE cluster. Awaits the results and, upon success, configures the kubeconfig file
    for kubernetes API validation.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    zone = user_config["gcp_zone"]
    node_count = user_config["gcp_cluster_node_count"]
    machine_type = user_config["gcp_cluster_machine_type"]

    # create the gke client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_gke_client()

    gke_task = gke_cluster.setup_gke_cluster(name, project, zone, node_count, machine_type, client)

    running = True
    while running:
        status = gke_cluster.gke_task_status(gke_task, project, zone, client)
        print(f"GKE Status {name}: {status.status.name}. {status.detail}")
        if status.status.name == "DONE":
            running = False
        else:
            sleep(2)

    # create entry for kubeconfig file
    gke_cluster.setup_cluster_auth_file(name, project, zone, client)


def destroy_gke(user_config):
    """Accepts a dict of validated user configs and uses it to destroy the specified
    GKE cluster. Awaits the results and confirms successful deletion.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    zone = user_config["gcp_zone"]

    # create the gke client. we're relying on the environment variable to be set for credentials
    client = gke_cluster.get_gke_client()

    gke_delete_task = gke_cluster.delete_gke_cluster(name, project, zone, client)

    running = True
    while running:
        status = gke_cluster.gke_task_status(gke_delete_task, project, zone, client)
        print(f"GKE Delete Status {name}: {status.status.name}. {status.detail}")
        if status.status.name == "DONE":
            running = False
        else:
            sleep(2)

    # delete entry in kubeconfig file
    gke_cluster.teardown_cluster_auth_file(name, project, zone)


def set_kubernetes_context(user_config):
    """Sets the kubernetes context to the provided name."""

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    zone = user_config["gcp_zone"]

    context_name = f"gke_{project}-{zone}-{name}"

    set_context_command = [
        "kubectl",
        "config",
        "use-context",
        context_name
    ]

    subprocess.run(set_context_command)


def deploy_test_container_image(user_config):
    """Accepts a dict of validated user configs and uses them to configure and send
    a cloud build job that copies the test script into the docker directory, creates
    the load test container image and uploads it to your GCP project's Container Registry.
    """

    # set variables from user config
    name = user_config["loadtest_name"]
    project = user_config["gcp_project_id"]
    image_tag = user_config["image_tag"]
    test_script = user_config["loadtest_script_name"]

    # copy test script into docker directory in prep for building
    copy_test_script_to_docker(test_script)

    # create build and storage clients
    build_client = cloud_build.get_build_client()
    storage_client = cloud_build.get_storage_client()

    # upload the tgz of the docker image directory to cloud storage
    bucket, blob = cloud_build.upload_source(project, storage_client)

    # trigger the build
    build_task = cloud_build.build_test_image(name, project, image_tag, bucket, blob, build_client)

    running = True
    while running:
        status = cloud_build.build_status(build_task, project, build_client)
        print(f"Cloud Build {name} {build_task}: {status}")
        if status == "SUCCESS":
            running = False
        else:
            sleep(2)


def deploy_looker_secret(user_config):
    """Accepts a dict of validated user configs and uses them to deploy looker website
    secrets. Since some of these values are optional if they are not present in the user
    config then that secret will be gracefully skipped.
    """

    # set host variable
    looker_host = user_config["looker_host"]

    # set variables if present
    looker_user = user_config.get("looker_user")
    looker_pass = user_config.get("looker_pass")
    looker_api_client_id = user_config.get("looker_api_client_id")
    looker_api_client_secret = user_config.get("looker_api_client_secret")

    # set host secret
    host_secret = "website-host"
    host_secret_value = {"host": looker_host}
    kubernetes_deploy.deploy_secret(host_secret, host_secret_value)

    # conditionally set secrets
    if looker_user and looker_pass:
        creds_secret = "website-creds"
        creds_secret_value = {"username": looker_user, "password": looker_pass}
        kubernetes_deploy.deploy_secret(creds_secret, creds_secret_value)

    if looker_api_client_id and looker_api_client_secret:
        api_secret = "api-creds"
        api_secret_value = {"client_id": looker_api_client_id, "client_secret": looker_api_client_secret}
        kubernetes_deploy.deploy_secret(api_secret, api_secret_value)


def deploy_oauth_secret(user_config):
    """Accepts a dict of validated user configs and uses them to deploy gcp oauth
    secrets. These are used to set up ingress for external deployments.
    """

    # set variables
    gcp_oauth_client_id = user_config["gcp_oauth_client_id"]
    gcp_oauth_client_secret = user_config["gcp_oauth_client_secret"]

    # set secrets
    oauth_secret = "iap-secret"
    oauth_secret_value = {"client_id": gcp_oauth_client_id, "client_secret": gcp_oauth_client_secret}
    kubernetes_deploy.deploy_secret(oauth_secret, oauth_secret_value)


def compare_tags(new_tag):
    """Accepts a container tag and compares it to the existing tag in the locust deployment.
    If the tags are the same then an exception is raised. Returns 1 if the tags are distinct.
    """

    # fetch kubeconfig file. Convert to a string for kubernetes client compatibility
    kubeconfig = str(SCRIPT_PATH.joinpath("rendered", "kubeconfig.yaml"))

    # fetch the current lm-pod deployment info
    locust_deployment = kubernetes_deploy.get_deployment("lm-pod", kubeconfig)

    # parse the image tag from the container
    image = locust_deployment.spec.template.spec.containers[0].image
    current_tag = image.split(":")[-1]

    if new_tag == current_tag:
        raise TagMatchError(new_tag)

    return 1


def deploy_locust(cycle=False):
    """Deploys the locust services and deployments to kubernetes. If the cycle argument is
    set to True then the deployments will be deleted prior to deployment (to be used during
    update commands).
    """

    render_path = SCRIPT_PATH.joinpath("rendered")

    # conditionally delete deployments
    if cycle:
        kubernetes_deploy.delete_deployment("lw-pod")
        kubernetes_deploy.delete_deployment("lm-pod")

    # roll out locust services and deployments
    locust_master = str(render_path.joinpath("locust-controller.yaml"))
    locust_worker = str(render_path.joinpath("locust-worker-controller.yaml"))

    wait_command = ["kubectl", "rollout", "status"]

    lm_command = APPLY_COMMAND + [locust_master]
    lm_wait_command = wait_command + ["deployment/lm-pod"]
    lw_command = APPLY_COMMAND + [locust_worker]
    lw_wait_command = wait_command + ["deployment/lw-pod"]

    locust_commands = [lm_command, lm_wait_command, lw_command, lw_wait_command]
    win_exec = ["cmd.exe", "/c"]
    for command in locust_commands:
        if os.name == "nt":
            command = win_exec + command
        subprocess.run(command)


def deploy_external():
    """Deploys the external services to kubernetes"""

    render_path = SCRIPT_PATH.joinpath("rendered")

    external_yamls = [
        str(render_path.joinpath("loadtest-cert.yaml")),
        str(render_path.joinpath("loadtest-ingress.yaml")),
        str(render_path.joinpath("config-default.yaml"))
    ]

    win_exec = ["cmd.exe", "/c"]
    for yml in external_yamls:
        command = APPLY_COMMAND + [yml]
        if os.name == "nt":
            command = win_exec + command
        subprocess.run(command)


def deploy_secondary():
    """Deploys the secondary services (prometheus, grafana, etc.) to kubernetes"""

    render_path = SCRIPT_PATH.joinpath("rendered")

    secondary_yamls = [
        str(render_path.joinpath("prometheus-config.yaml")),
        str(render_path.joinpath("prometheus-controller.yaml")),
        str(render_path.joinpath("grafana-config.yaml")),
        str(render_path.joinpath("grafana-controller.yaml"))
    ]

    win_exec = ["cmd.exe", "/c"]
    for yml in secondary_yamls:
        command = APPLY_COMMAND + [yml]
        if os.name == "nt":
            command = win_exec + command
        subprocess.run(command)
