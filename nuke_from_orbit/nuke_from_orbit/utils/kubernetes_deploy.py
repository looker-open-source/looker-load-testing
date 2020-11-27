from kubernetes import client, config, utils
from time import sleep, time
from pathlib import Path


def deploy_from_yaml(yaml_file, config_file):
    config.load_kube_config(config_file=config_file)
    k8_client = client.ApiClient()
    utils.create_from_yaml(k8_client, yaml_file)


def wait_for_deployment(deployment_name, config_file, timeout=60):
    config.load_kube_config(config_file="./rendered/kubeconfig.yaml")

    with client.ApiClient() as api_client:
        api_instance = client.AppsV1Api(api_client)
        start = time()
        while time() - start < timeout:
            sleep(2)
            resp = api_instance.read_namespaced_deployment(deployment_name, "default")
            dstatus = resp.status

            spec_replicas = resp.spec.replicas
            spec_generation = resp.metadata.generation

            ds_replicas = dstatus.replicas
            ds_updated = dstatus.updated_replicas
            ds_available = dstatus.available_replicas
            ds_generation = dstatus.observed_generation

            updated_replica_match = ds_updated == spec_replicas
            replica_match = ds_replicas == spec_replicas
            available_replica_match = ds_available == spec_replicas
            generation_match = ds_generation >= spec_generation

            if (updated_replica_match and replica_match and available_replica_match and generation_match):
                print("Deployment ready!")
                return True
            else:
                print(f"Replicas: {ds_replicas}. Updated: {ds_updated}. Available: {ds_available}")

        print("Timeout!")


def delete_deployment(deployment_name, config_file):
    config.load_kube_config(config_file=config_file)

    with client.ApiClient() as api_client:
        api_instance = client.AppsV1Api(api_client)
        api_instance.delete_namespaced_deployment(deployment_name, "default")


if __name__ == "__main__":
    deploy_from_yaml()
    wait_for_deployment("lm-pod")
