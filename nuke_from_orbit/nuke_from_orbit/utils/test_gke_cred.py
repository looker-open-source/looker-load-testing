import gke_cluster
from google.oauth2 import service_account
from time import sleep

name = "pytest-cluster"
project = "jcp-loadtest-sandbox"
zone = "us-central1-c"
node_count = 1
machine_type = "e2-standard-2"

#  creds = service_account.Credentials.from_service_account_file("../../jcp-loadtest-sandbox-9b4258773b60.json")
client = gke_cluster.get_gke_client()

task = gke_cluster.setup_gke_cluster(name, project, zone, node_count, machine_type, client)

running = True
while running:
    status = gke_cluster.gke_task_status(task, project, zone, client)
    print(f"Status: {status.status.name}. {status.detail}")
    if status.status.name == "DONE":
        running = False
    else:
        sleep(2)

gke_cluster.setup_cluster_auth_file(name, project, zone, client)
