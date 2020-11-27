from google.cloud import container_v1
from jinja2 import Template
from pathlib import Path


def get_gke_client(credentials=None):
    client = container_v1.ClusterManagerClient(credentials=credentials)

    return client


def setup_gke_cluster(name, project, zone, node_count, machine_type, client):
    parent = f"projects/{project}/locations/{zone}"

    cluster = {
        "name": name,
        "release_channel": {
            "channel": "REGULAR"
        },
        "node_pools": [
            {
                "name": "load-test-pool",
                "initial_node_count": node_count,
                "config": {
                    "machine_type": machine_type,
                    "oauth_scopes": [
                        "https://www.googleapis.com/auth/cloud-platform"
                    ]
                }
            }
        ]
    }

    request = container_v1.types.CreateClusterRequest(parent=parent, cluster=cluster)
    task = client.create_cluster(request=request)

    return task.name


def delete_gke_cluster(name, project, zone, client):
    cluster_name = f"projects/{project}/locations/{zone}/clusters/{name}"
    request = container_v1.types.DeleteClusterRequest(name=cluster_name)
    task = client.delete_cluster(request=request)

    return task.name


def gke_task_status(name, project, zone, client):
    task_name = f"projects/{project}/locations/{zone}/operations/{name}"
    request = container_v1.types.GetOperationRequest(name=task_name)
    task_status = client.get_operation(request=request)

    return task_status


def setup_cluster_auth_file(name, project, zone, client):
    cluster_name = f"projects/{project}/locations/{zone}/clusters/{name}"
    request = container_v1.types.GetClusterRequest(name=cluster_name)
    cluster = client.get_cluster(request=request)

    ca_cert = cluster.master_auth.cluster_ca_certificate
    endpoint = cluster.endpoint

    vals = {
        "name": name,
        "project": project,
        "zone": zone,
        "ca_cert": ca_cert,
        "endpoint": endpoint
    }

    script_path = Path(__file__).parent
    kubeconfig_template = script_path.joinpath("templates", "kubeconfig.yaml")
    kubeconfig_rendered = script_path.joinpath("rendered", "kubeconfig.yaml")
    template = kubeconfig_template.read_text()
    rendered = Template(template).render(**vals)

    with open(kubeconfig_rendered, "w") as f:
        f.write(rendered)

    return kubeconfig_rendered.resolve()
