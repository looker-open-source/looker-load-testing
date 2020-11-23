from google.cloud import container_v1


def get_gke_client(credentials):
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
