## Introduction

![nuke-from-orbit](https://i.imgflip.com/1o9ejc.jpg)

Sometimes you need a little more boom, so let's rain fire from the clouds... it's the only way to be sure.

This section contains a framework for a Kubernetes-based distributed LocustIO cluster. Provided is an example of how to
run a "real browser" based test of a looker dashboard.

The instructions below are for GCP, but this pattern can be run on any Kubernetes cluster in any environment with some modifications. At a high level
the steps are:

1. Build a Docker image of your locust tests
2. Spin up a Kubernetes cluster
3. Create the master and worker deployments, the service, and any related secrets
4. Provide ingress, secured with HTTPS and some form of authentication (IAP in this case)
5. (Optional) Wire it up to a monitoring solution, like Grafana

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

First, you will need access to GCP and have installed the [gcloud command line utility](https://cloud.google.com/sdk/install).

You will need access to a unix-like system and a bash shell. OSX or Linux will work fine. Linux subsystem for Windows
should also work, but I have not tested these instructions on Windows.

You will need a working version of python 3.7. I would recommend making use of [pyenv](https://github.com/pyenv/pyenv) to manage your Python
installations. You will also need [Pipenv](https://pipenv-fork.readthedocs.io/en/latest/) to manage the virtual environment and the required library installation.

You will also need [jq](https://stedolan.github.io/jq/), a command-line JSON parsing utility.

Finally, in order for https and IAP to work correctly you will need to own or have control of a registered domain. You should
have the ability to create an A-Record from that domain's DNS.

## Before you begin

The following steps need to be completed before you begin to deploy the load tester. They should only need to be done
one time per project - during subsequent deployments you won't need to repeat these steps (unless you delete any of the
assets of course)

### From the GCP Console

1. Create a suitable GCP Project. I recommend creating a new unique project for the load testing tool. We don’t want to run the risk of trampling other projects you may be working on.
2. Create a service account in your new project:
    * Navigate to IAM-Admin -> Service Accounts, click Create Service Account at top of page.
    * Follow the instructions to create a service account:
    * On the second page when prompted for roles you can give it Project Editor.
    * On the third page you do not need to grant any user access to the Service Account.
    * Back on the main page find your new service account and under the “Actions” menu choose “Create Key”:
        * Select JSON key and a credentials json file will be downloaded to your system.

> ⚠ **WARNING: This file should be considered sensitive and should be secured appropriately.**

3. Assign IAP WebApp User Permissions to yourself:
    * Navigate to IAM-Admin -> IAM
    * Find yourself in the list of users and accounts (i.e. the email address you want to use to log in to the tool). Click the Edit icon on the right.
    * Click ‘Add Another Role’ and select ‘IAP-secured Web App User`
4. Create your OAuth Consent Page:
    * Navigate to API & Services -> Oauth Consent Screen. Create an app:
        * Set the type to Internal (unless you need to share permissions external to your org)
        * Enter an App Name, User Support Email and Developer Contact Information.
    * The next page should be Scopes - do not fill in anything.
5. Create Oauth Credentials:
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

Using `pipenv`, install the required Python libraries:

    $ pipenv install --ignore-pipfile --python 3.7


### Activate Your gcloud Service Account

You will need to activate the service account using the credentials file you generated above:

    $ gcloud auth activate-service-account foobar@myproject.iam.gserviceaccount.com --key-file path/to/credentials.json

You will likely need to (re)initialize your gcloud profile:

    $ gcloud init

Follow the interactive steps to select your service account and relevant GCP Project.

### Enable APIs

The Following services should be enabled in your project:

    $ gcloud services enable \
      cloudbuild.googleapis.com \
      compute.googleapis.com \
      container.googleapis.com \
      containeranalysis.googleapis.com \
      containerregistry.googleapis.com \
      iap.googleapis.com


## Deploy The Load Tester

### Write your test manifest

**Very Important!** Modify the contents of `docker-image/locust-tasks/tasks.py` to suit your testing criteria

> The example `tasks.py` outlines a standard dashboard rendering performance test. Near the top of the file you will
> want to modify the `SITE` and `DASH_ID` variables to match the Looker instance you are testing and the relevant
> dashboard id. Different testing goals will require specific test code - Locust is flexible enough to handle just about
> any kind of test you can think of!

### Set Config Parameters

Navigate to the nuke-from-orbit directory and create a json file called ‘config.json’. You’ll need to add entries for the following items:

* loadtest_name: A unique identifier for your load test
* loadtest_dns_domain: The DNS domain/subdomain name
* gcp_project_id: The project ID of your GCP project
* gcp_region: The GCP region
* gcp_zone: The GCP zone
* gcp_oauth_client_id: The OAuth Client ID you generated earlier
* gcp_oauth_client_secret: The OAuth Client Secret you generated earlier
* gcp_cluster_node_count: How many nodes should be included in the load test cluster
* gcp_cluster_machine_type: What compute instance machine type should be used? (Almost certainly a C2 type instance)
* looker_user: The username of the Looker instance you are testing
* looker_pass: The password of the Looker instance you are testing

Your config may look something like this:

```
{
  "loadtest_name": "my-gke-load-test-name",
  "loadtest_dns_domain": "loadtest.company.com",
  "gcp_project_id": "my-gcp-project-name",
  "gcp_region": "us-central1",
  "gcp_zone": "us-central1-c",
  "gcp_oauth_client_id": "abc123xyz.apps.googleusercontent.com",
  "gcp_oauth_client_secret": "foobarbaz",
  "gcp_cluster_node_count": 3,
  "gcp_cluster_machine_type": "c2-standard-8",
  "looker_user": "me@company.com",
  "looker_pass": "abc_123_xyz"
}
```

> ⚠ Warning: This config contains sensitive information, so protect this file like any other credentials.

### Deploy!

1. Navigate to the project root and activate your pipenv environment:

    $ pipenv shell

2. Navigate to the nuke-from-orbit directory and kick off the deployment!

    $ cd nuke-from-orbit
    $ ./loadtester setup


> ★ Tip: The script will take around 5 minutes to complete depending on what kind of instances it’s creating. It also takes a distressingly long time for the GCP Managed Cert to provision (like… 15-20 minutes or so)

3. The final output will provide additional instructions for how to set up your DNS entry to allow for access to the
   load tester. Set up an A Record for the wildcard domain to the specified IP address.

### Accessing the Load Tester

For the purposes of an example, let’s say the `load_test_dns_domain` parameter in your `config.json` was set to `my-loadtest.company.com`. Once everything has some time to bake
you will be able to access your load tester at `https://locust.my-loadtest.company.com`. This will be where you kick off load tests. It also has some graphs and metrics available.

### Scaling

Scaling up the number of simulated users will require an increase in the number of Locust
worker pods. To increase the number of pods deployed by the deployment, Kubernetes offers the ability to resize
deployments without redeploying them. For example, the following command scales the pool of Locust worker pods to 20:

        $ kubectl scale deployment/lw-pod --replicas=20

### Monitoring

While we can now load test Looker at scale, testing without monitoring is like shooting in the dark. While the locust UI
provides some good real-time monitoring to truly make use of the data you collect I would suggest integrating the locust
metrics with your internal Looker and other infrastructure monitoring. Keeping with the example DNS from above the load
tester makes the Locust metrics available at `https://locust-metrics.myloadtest.company.com/metrics`. The metrics are
presented in Prometheus format and should be ingestable by any modern monitoring tool.

## Cleaning up

Once you are done load testing and exporting data you can tear down your cluster to avoid additional costs. From the
nuke-from-orbit directory:

    $ ./loadtester teardown

You will likely want to clean up your DNS entry as well.

To kick off another test simply rerun the `./loadtester setup` command and you're back in business!

## Additional Reading

1. [Locust Documentation](https://docs.locust.io/en/0.14.6/)
2. [Managed Certificates GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs)
3. [IAP with GKE](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#oauth-configure)
