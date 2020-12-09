from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
from time import sleep, time


def deploy_from_yaml(yaml_file, namespace="default"):
    """Deploys a multi-part yaml manifest to kubernetes"""

    config.load_kube_config()
    k8_client = client.ApiClient()
    utils.create_from_yaml(k8_client, yaml_file, namespace=namespace)


def get_deployment(deployment_name, namespace="default"):
    """Accepts a deployment name and returns the specified deployment object from kubernetes.
    Can be used to extract relevant metadata such as the version tag.
    """

    config.load_kube_config()

    with client.ApiClient() as api_client:
        api_instance = client.AppsV1Api(api_client)
        resp = api_instance.read_namespaced_deployment(deployment_name, namespace)

    return resp


def wait_for_deployment(deployment_name, namespace="default", timeout=60):
    """Polls for the status of a given deployment. When successful, a success message is
    printed and boolean True is returned. If deployment is not ready by the specified
    timeout argument (default 60 seconds) a timeout exception is thrown.
    """

    config.load_kube_config()

    with client.ApiClient() as api_client:
        api_instance = client.AppsV1Api(api_client)
        start = time()
        while time() - start < timeout:
            sleep(2)
            resp = api_instance.read_namespaced_deployment(deployment_name, namespace)
            dstatus = resp.status

            # parsing a bunch of info for easy comparison
            spec_replicas = resp.spec.replicas
            spec_generation = resp.metadata.generation

            ds_replicas = dstatus.replicas
            ds_updated = dstatus.updated_replicas
            ds_available = dstatus.available_replicas
            ds_generation = dstatus.observed_generation

            # creating booleans for relevant comparisons
            updated_replica_match = ds_updated == spec_replicas
            replica_match = ds_replicas == spec_replicas
            available_replica_match = ds_available == spec_replicas
            generation_match = ds_generation >= spec_generation

            # checking if the deployment is ready
            if (updated_replica_match and replica_match and available_replica_match and generation_match):
                print("Deployment ready!")
                return True
            else:
                print(f"Replicas: {ds_replicas}. Updated: {ds_updated}. Available: {ds_available}")

        # TODO: generate and throw an actual exception
        print("Timeout!")


def deploy_secret(secret_name, secret_data, namespace="default"):
    """Creates or updates a secret with the values specified in the secret_data param.
    This param must be a dict where the key is the entry name and the value is the secret
    value (e.g. `{"username": "dudefella"}'). If the secret already exists then it will
    be patched instead. Returns the secret object that has been created/updated.
    """

    secret_metadata = {"name": secret_name, "namespace": "default"}
    api_version = "v1"
    kind = "Secret"

    config.load_kube_config()
    k8 = client.CoreV1Api()
    body = client.V1Secret(api_version=api_version, kind=kind, metadata=secret_metadata, string_data=secret_data)

    # Try the post request. If it fails, handle the 409 response by trying a patch request instead
    try:
        resp = k8.create_namespaced_secret(namespace, body)
    except ApiException as e:
        if e.status == 409:
            print("Secret already exists! Updating...")
            resp = k8.patch_namespaced_secret(name=secret_name, namespace=namespace, body=body)

    return resp


def delete_deployment(deployment_name):
    """Deletes a deployment - usually as a part of a config refresh."""

    config.load_kube_config()

    with client.ApiClient() as api_client:
        api_instance = client.AppsV1Api(api_client)
        api_instance.delete_namespaced_deployment(deployment_name, "default")
