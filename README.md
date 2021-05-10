## Introduction

![nuke-from-orbit](https://i.imgflip.com/1o9ejc.jpg)

Nuke From Orbit (aka NFO) is a framework for load testing Looker instances. It is designed to be easy to set up, easy to
use, and approachable for just about anybody who wants to answer questions about how their infrastructure is performing.

NFO is designed to perform either API-based or Browser-based load testing via distributed Kubernetes clusters in the
cloud (hence the name -  we're raining fire from the clouds...).

NFO is a Python application - it makes use of the battle-tested [Locust.io](https://locust.io/) framework and adds
the ability to run browser-based tests in a containerized/orchestrated environment (i.e. kubernetes).

## Status and Support

NFO is NOT supported or warranteed by Looker in any way. Please do not contact Looker support for issues with NFO.

## Why browser-based tests?

Browser-based load testing is a relatively new concept - in the past the expense of running enough browsers to
stress-test an instance was cost-prohibitive. This challenge has been mitigated by the economies of scale that cloud
computing provides.

Browser tests offer several clear advantages. First, the writing of tests is significantly easier - simply use browser
automation tools like selenium to dictate what you want to happen in the browser - no need to simulate the same process
with dozens (if not hundreds) of API calls. For example, a Looker dashboard load is comprised of many many different API
calls... but with browser based testing you simply load the dashboard URL and that's it.

Second, there are some elements of Looker performance that cannot be captured by API tests. For example, loading a
dashboard requires the final graphics be rendered in the page. Browser-based tests can capture this time.

There is a trade-off - while cloud infrastructure makes browser-based testing affordable it is still more expensive than
API-based testing. If you can frame your tests as pure http/API calls then you will be able to generate far more
simulated traffic at a much lower price. NFO can handle both types of tests (and combinations of them within the same
test script!)

## A note on scaling

Running headless browsers is a CPU-bound process. For this reason, if you are trying to time dashboard load times with
Selenium I strongly recommend using CPU-optimized machine types for your nodes. The example below uses the CPU-optimized
C2 machine types for demonstration purposes. A reading of the Kubernetes deployment config files reveals that the worker
pods request 1 core. A good rule of thumb is each worker can simulate 2 real browsers with 1 core, so if you wanted to
simulate 20 browsers you will need approximately >10 cores in your cluster. (slightly more to handle some overhead -
e.g. The master pod itself as well as Prometheus and Grafana if you want the dashboards) Attempting to run workers with
less CPU will result in degraded dashboard loading performance, leading to incorrect test results, as well as risk of
pod eviction.

One more note: For these tests, one browser does not equal one user - each browser can make a new dashboard request
every second or two, meaning one browser can simulate the traffic of several human users. If you see an RPS value of 20
during your tests, that means 20 dashboard loads per second, or 1200/minute. Assuming a person spends about 30 seconds
on a dashboard this is equivalent to approximately 600 concurrent users.

## Prerequisites

First, you will need access to GCP and have Editor access to a GCP Project

You will need a working version of python 3.8+. I would recommend making use of [pyenv](https://github.com/pyenv/pyenv) to manage your Python
installations.

For the moment you will need to use developer installation workflows (this will change soon). This means you will need
[poetry](https://python-poetry.org/docs/) to handle the installation.

You will also need [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/), the command line tool for interacting with kubernetes


Finally, in order to access your NFO instance via the web you will need to own or have control of a registered domain. You should
have the ability to create an A-Record from that domain's DNS.

## Before you begin

The following steps need to be completed before you begin to deploy the load tester. They should only need to be done
one time per project - during subsequent deployments you won't need to repeat these steps (unless you delete any of the
assets of course)

### From the GCP Console

1. Create a suitable GCP Project. I recommend creating a new unique project for the load testing tool. We don’t want to run the risk of trampling other projects you may be working on.
2. Ensure the correct APIs have been enabled. From the GCP console open a [cloud shell](https://cloud.google.com/shell) and run the following command:

    $ gcloud services enable \
      cloudbuild.googleapis.com \
      compute.googleapis.com \
      container.googleapis.com \
      containeranalysis.googleapis.com \
      containerregistry.googleapis.com \
      iap.googleapis.com

3. Create a service account in your new project:
    * Navigate to IAM-Admin -> Service Accounts, click Create Service Account at top of page.
    * Follow the instructions to create a service account:
    * On the second page when prompted for roles you can give it Project Editor.
    * On the third page you do not need to grant any user access to the Service Account.
    * Back on the main page find your new service account and under the “Actions” menu choose “Create Key”:
        * Select JSON key and a credentials json file will be downloaded to your system.

> ⚠ **WARNING: This file should be considered sensitive and should be secured appropriately.**

> **Note:** These next steps are only required if you plan on using External Mode to access the load tester via the web

4. Assign IAP WebApp User Permissions to yourself:
    * Navigate to IAM-Admin -> IAM
    * Find yourself in the list of users and accounts (i.e. the email address you want to use to log in to the tool). Click the Edit icon on the right.
    * Click ‘Add Another Role’ and select ‘IAP-secured Web App User`
5. Create your OAuth Consent Page:
    * Navigate to API & Services -> Oauth Consent Screen. Create an app:
        * Set the type to Internal (unless you need to share permissions external to your org)
        * Enter an App Name, User Support Email and Developer Contact Information.
    * The next page should be Scopes - do not fill in anything.
6. Create Oauth Credentials:
    * Navigate to API & Services -> Credentials.
    * Click Create Credentials.
        * Select Oauth Client Id.
        * For Application Type, select Web Application.
        * Add a name and click Create.
    * You will find your Client ID and Client Secret in the upper right corner of the next page. Copy them somewhere - we’ll need them in a minute.
    * On this same page add an Authorized Redirect URI using the following template (replace `{{CLIENT_ID}}` with your new Client ID): `https://iap.googleapis.com/v1/oauth/clientIds/{{CLIENT_ID}}:handleRedirect`

### Clone The Repo

In your development environment, clone the load testing repo:

    $ git clone https://github.com/llooker/looker-load-testing.git
    $ cd looker-load-testing

### Install Python libraries

From the project root directory use poetry to install the required libraries. This will also create a virtual
environment for you.

    $ poetry install

After the install completes you can access this new virtual environment with the following command:

    $ poetry shell


## Deploy The Load Tester

### Write your test manifest

Navigate to the `locust_test_scripts` directory and create your test script. Documentation for standard http tests can be found
[here](https://docs.locust.io/en/0.14.6/writing-a-locustfile.html)

Examples for browser-based tests can be found in `locust_test_scripts`.

You will need to pass the relevant script name into the config file - see below for more details.

> The example `defaut_dashboard_loadtest` outlines a standard dashboard rendering performance test. If you want to use this with
> your own instance, near the top of the file you will want to modify the `DASH_ID` variables to match the Looker instance
> you are testing and the relevant dashboard id. Different testing goals will require specific test code - Locust is flexible enough
> to handle just about any kind of test you can think of!

### Copy service account file to credentials directory

In order for NFO to authenticate to GCP correctly you must copy the service account json you created above to the
`credentials` directory. You will refer to this file in the config file you create next.

### Set Config Parameters

Navigate to the nuke-from-orbit/configs directory and create a json file called ‘config.yaml’. You’ll need to add entries for the following items:

* **gke_cluster**
  - **gcp_project_id**: The project ID of your GCP project
  - **gcp_zone**: The GCP zone
  - **gcp_cluster_node_count**: How many nodes should be included in the load test cluster
  - **gcp_cluster_machine_type**: What compute instance machine type should be used? (Almost certainly a C2 type instance)
  - **gcp_service_account_file**: The name of the service account file you generated from GCP. Just the file name, not
    the path
* **loadtester**
  - **loadtest_name**: A unique identifier for your load test
  - **loadtest_step_load**: ("true"|"false") Should locust run in [step mode](https://docs.locust.io/en/0.14.6/running-locust-in-step-load-mode.html)
  - **loadtest_worker_count**: How many workers should be created
  - **loadtest_script_name**: The name of the script that contains your test logic. Only include the script's file name, not the rest of the path
* **looker_credentials**
  - **looker_host**: The URL of the Looker instance you are testing
  - **looker_user**: (Optional) The username of the Looker instance you are testing
  - **looker_pass**: (Optional) The password of the Looker instance you are testing
  - **looker_api_client_id**: (Optional) The API client_id of the Looker instance you are testing
  - **looker_api_client_secret**: (Optional) The API client_secret of the Looker instance you are testing
* **external**
  - **gcp_oauth_client_id**: (External Mode) The OAuth Client ID you generated earlier
  - **gcp_oauth_client_secret**: (External Mode) The OAuth Client Secret you generated earlier
  - **loadtest_dns_domain**: The DNS domain/subdomain name you want to use to access the NFO resources

Your config may look something like this:

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

> ⚠ Warning: This config contains sensitive information, so protect this file like any other credentials.

### Deploy!

Navigate to the nuke-from-orbit directory and kick off the deployment!

    $ nuke setup --config-file config.yaml --external

> ★ Tip: The script will take around 5 minutes to complete depending on what kind of instances it’s creating.

When the script concludes it will output some final instructions. If you've chosen to run in external mode you will need
to set up a DNS A Record for the printed IP address and URL.

Some additional instructions will be printed in case you wish to port-forward the locust services for immediate access.
If you're running in external mode the google-managed SSL certificate will take 15-20 minutes to provision, but you can
port-forward immediately. See the [kubernetes documentation](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/) for more details.


### Updating the test

Since the test script is a part of the container you build and deploy any updates to the test script will require
building and deploying a new container. This process has been automated with an `update` command. Make your required
changes to the test script and then run the following command:

    $ nuke update test --config-file config.yaml --tag <tag>

This will rebuild the container and execute the correct steps to update the kubernetes deployment. These changes will be
available immediately upon completion of the command - no need to redeploy the ingress or wait for DNS this time around!

> Note: You must provide a unique tag to trigger a rebuild - attempting to use the same tag will result in an error.
> Consider using a tag that includes a version number. When you first deploy the load tester it automatically creates a
> tag of 'v1' so one good option is to simply increment the number, e.g. 'v2', 'v3', etc.

### Updating the config

If your updates involve changes to just the config you can make use of the following command:

    $ nuke update config --config-file config.yaml

This will redeploy the master/worker deployments with the updated config - this is even faster than the test update
command since there's no need to build a new container image!


#### Accessing the UI via the web

For the purposes of an example, let’s say the `load_test_dns_domain` parameter in your `config.yaml` was set to `my-loadtest.company.com`. Once everything has some time to bake
you will be able to access your load tester at `https://locust.my-loadtest.company.com`.


### Scaling

Scaling up the number of simulated users will require an increase in the number of Locust
worker pods. To increase the number of pods deployed by the deployment, Kubernetes offers the ability to resize
deployments without redeploying them. This can be done by editing the `loadtest_worker_count` field in the config
file and triggering a config update (see above). You can also make use of imperitive `kubectl` commands. For
example, the following command scales the pool of Locust worker pods to 20:

        $ kubectl scale deployment/lw-pod --replicas=20

### Monitoring

In addition to the locust interface itself, NFO makes available a grafana instance with a pre-configured dashboard. You
can access this at `https://grafana.my-loadtest.company.com` (following the example from above - make sure you use your
proper domain!) if you've deployed in external mode. If you're port forwarding you can forward the `grafana` service's port 80 to access.

The preconfigured dashboard includes some locust tiles as well as preset looker monitoring for looker instances running
on GCP - you'll need to create a generic Google Cloud Monitoring datasource - follow [grafana's documentation](https://grafana.com/docs/grafana/latest/datasources/cloudmonitoring/)
for more details. Grafana can handle just about any standard data source so feel free to modify to suit your needs!

### Multiple load tests

NFO supports deploying multiple load tests at any given time. Simply create a new config yaml in your `configs`
directory with your desired configuration and deploy as normal, referencing the new config file in your `--config-file`
parameter! NFO will handle setting up your kubectl context for you.

## Cleaning up

Once you are done load testing and exporting data you can tear down your cluster to avoid additional costs. From the
nuke-from-orbit directory:

    $ nuke teardown --config-file config.yaml

You will likely want to clean up your DNS entry as well.

To kick off another test simply rerun the `nuke setup` command and you're back in business!

## Persistent Test Data

By default, NFO deploys a special storage disk that is used as a persistent volume to store locust data. This disk does
not get torn down with the rest of the cluster and will get re-attached when the same config file is used to deploy a
new cluster. The intention of this disk is to allow for test data to "survive" cluster teardowns without the need to
keep your expensive kubernetes infrastructure running. Each test config (as defined by the config yaml) will have its
own disk created.

Should you wish to export your Locust test data to another source (e.g. BigQuery etc.) you can make use of the
[Prometheus API](https://prometheus.io/docs/prometheus/latest/querying/api/)

Should you wish to remove the persistent disk during teardown you can make use of the `--all` flag in the teardown
command:

    $ nuke teardown --config-file config.yaml --all

## Local Mode

You can run locust in local mode - this may be desirable during test development for rapid iteration. You will need to
make sure you have a suitable version of [Chromedriver](https://chromedriver.chromium.org/downloads) installed. This
**must** match the version of Chrome you have on your system... mismatches in versions will cause errors!

Once you have Chromedriver installed you can start a locust instance with the following command:

    $ locust -f path/to/test-script.py


(replace the path with the correct path to the load test you want to run)

Locust will by default be made available on localhost:8089.

You will very likely need to set some environment variables in order to properly run your tests - these variables will
likely be:

- HOST (your looker host)
- USERNAME (the username you will log in with)
- PASS (the password associated with the username you're using)

## Additional Reading

1. [Locust Documentation](https://docs.locust.io/en/0.14.6/)
2. [Managed Certificates GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs)
3. [IAP with GKE](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#oauth-configure)
