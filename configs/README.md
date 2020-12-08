## Configs

Place your config yaml files here! You'll refer to them via the `--config-file` argument in your commands.

An example config yaml may look something like this:

```
gke_cluster:
  gcp_project_id: my-gcp-project
  gcp_zone: us-central1-c
  gcp_cluster_node_count: 3
  gcp_cluster_machine_type: c2-standard-8
  gcp_service_account_file: my-service-account-file.json
loadtester:
  loadtest_name: demo-loadtest
  loadtest_step_load: "true"
  loadtest_worker_count: 20
  loadtest_script_name: default_dashboard_loadtest.py
looker_credentials:
  looker_host: https://looker.company.com
  looker_user: me@company.com
  looker_pass: abc123fakepassword
external:
  gcp_oauth_client_id: abc123.apps.googleusercontent.com
  gcp_oauth_client_secret: 789xzyfakeclient
  loadtest_dns_domain: py-loadtest.colinpistell.com
```
