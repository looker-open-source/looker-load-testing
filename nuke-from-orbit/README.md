## Introduction

![nuke-from-orbit](https://i.imgflip.com/1o9ejc.jpg)

Sometimes you need a little more boom, so let's rain fire from the clouds... it's the only way to be sure.

This section contains a framework for a Kubernetes-based distributed LocustIO cluster. Provided is an example of how to
run a "real browser" based test of a looker dashboard.

This guide is derived from the official GCP Locust/Kubernetes tutorial, which can be found
[here.](https://cloud.google.com/solutions/distributed-load-testing-using-gke)

The instructions below are for GCP, but this can be run on any Kubernetes cluster in any environment. At a high level
the steps are:

1. Build a Docker image of your locust tests
2. Spin up a Kubernetes cluster
3. Create the master and worker deployments, the service, and any related secrets
4. Wire it up to a monitoring solution, like Grafana
5. Provide ingress, secured with HTTPS and some form of authentication (IAP in this case)

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

In order for https and IAP to work correctly you will need to own or have control of a registered domain. You should
have the ability to create an A-Record from that domain's DNS.

## Before you begin

The following steps need to be completed before you begin to deploy the load tester. They should only need to be done
one time per project - during subsequent deployments you won't need to repeat these steps (unless you delete any of the
assets of course)

Open Cloud Shell to execute the commands listed in this tutorial.

### Enable APIs

The Following services should be enabled in your project: Cloud Build, Kubernetes Engine, Cloud Storage

    $ gcloud services enable \
      cloudbuild.googleapis.com \
      compute.googleapis.com \
      container.googleapis.com \
      containeranalysis.googleapis.com \
      containerregistry.googleapis.com

### Static IP and DNS

Create a static IP. This will be used by our ingress controller and will allow you to set up your DNS records just
once:

    $ gcloud compute addresses create loadtest-address --global
    $ gcloud compute addresses describe loadtest-address --global

Then follow the instructions for your DNS provider to create an A-Record that maps the IP address you just created to
the following value: `*.loadtest.[DOMAIN]` (replace [DOMAIN] with your domain name, e.g. `example.com`)

### OAuth Config

In order to use Identity Aware Proxy (IAP) you will need to set up OAuth:

1. Follow the instructions for [Configuring the OAuth Consent
   Screen](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#oauth-configure)

2. Follow the instructions for [Creating OAuth Credentials](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#oauth-credentials).
   Make a note of your client-id and client-secret

### Download the code

Clone this repo in a local directory on your cloud shell environment and cd to the `nuke-from-orbit` directory:

        $ git clone https://github.com/JCPistell/looker-load-testing.git
        $ cd looker-load-testing/nuke-from-orbit

## Deploy The Load Tester

Open Cloud Shell to execute the commands listed in this tutorial.

Define environment variables for the project id, region and zone you want to use for this tutorial.

    $ PROJECT=$(gcloud config get-value project)
    $ REGION=us-central1
    $ ZONE=${REGION}-c
    $ CLUSTER=gke-load-test
    $ gcloud config set compute/region $REGION
    $ gcloud config set compute/zone $ZONE

1. Create GKE cluster. In this example we're using a cluster of 3 c2-standard-8 machines but you may need a different
   setup depending on your load tests. Note the cluster version - make sure you're using >= 1.16.9.

        $ gcloud container clusters create $CLUSTER \
          --zone $ZONE \
          --scopes "https://www.googleapis.com/auth/cloud-platform" \
          --num-nodes "3" \
          --machine-type "c2-standard-8" \
          --cluster-version "1.16.9-gke.6"

        $ gcloud container clusters get-credentials $CLUSTER \
          --zone $ZONE \
          --project $PROJECT


2. **Very Important!** Modify the contents of `docker-image/locust-tasks/tasks.py` to suit your testing criteria

> The example `tasks.py` outlines a standard dashboard rendering performance test. Near the top of the file you will
> want to modify the `SITE` and `DASH_ID` variables to match the Looker instance you are testing and the relevant
> dashboard id. Different testing goals will require specific test code - Locust is flexible enough to handle just about
> any kind of test you can think of!

3. Build docker image and store it in your project's container registry. Note this command assumes you are in the
   `nuke-from-orbit` directory.

        $ gcloud builds submit --tag gcr.io/$PROJECT/locust-tasks:latest docker-image/.

4. Ensure you are using the latest version of the code and are in the repo's `nuke-from-orbit` directory - all
  commands assume that as your working directory.

        $ git checkout master
        $ git pull
        $ cd <path to nuke-from-orbit>

5. Replace [PROJECT_ID] in locust-controller.yaml with the deployed endpoint and project-id respectively. Note that if
   you haven't pulled any new updates this step may be unnecessary, but it's safe to perform every time.

        $ sed -i -e "s/\[PROJECT_ID\]/$PROJECT/g" kubernetes-config/locust-controller.yaml

   If you want to enable step-mode you can change the `LOCUST_STEP` variables from `"false"` to `"true"` in
   `locust-controller.yaml` - note that you must do this in both the `lm-pod` and `lw-pod` Deployments.

6. Replace [DOMAIN] in loadtest-cert.yaml and loadtest-ingress.yaml with your domain
   name: (be sure to replace the placeholder with your actual domain name! - e.g. `example.com`) Note that if
   you haven't pulled any new updates this step may be unnecessary, but it's safe to perform every time.

        $ sed -i -e "s/\[DOMAIN\]/<your domain name>/g" kubernetes-config/loadtest-cert.yaml
        $ sed -i -e "s/\[DOMAIN\]/<your domain name>/g" kubernetes-config/loadtest-ingress.yaml

7. Deploy the managed certificate:

        $ kubectl apply -f kubernetes-config/loadtest-cert.yaml

8. Create a Kubernetes secret called `iap-secret` for your OAuth client-id and client-secret: (be sure to replace the
   placeholders with your actual values!)

        $ echo -n <your_client_id> > client_id.txt
        $ echo -n <your_client_secret> > client_secret.txt
        $ kubectl create secret generic iap-secret --from-file=client_id=./client_id.txt --from-file=client_secret=./client_secret.txt

9. Deploy the backend config:

        $ kubectl apply -f kubernetes-config/config-default.yaml

10. Create a Kubernetes secret called `website-creds` that contains two entries - `username` and `password` - that tie to
   the Looker instance you will be logging into (the instance you specified in step 2):

        $ echo -n <your username> > username.txt
        $ echo -n <your password> > pass.txt
        $ kubectl create secret generic website-creds --from-file=username=./username.txt --from-file=password=./pass.txt

11. Deploy Locust master and worker nodes:

        $ kubectl apply -f kubernetes-config/locust-controller.yaml


### Better Monitoring and Data Retention

While we can now load test Looker at scale the data available from locust out of the box leaves something to be desired.
Summary metrics are available for download, but the rich time series data is not, and the charts reset on every refresh.
We can probably do better, and fortunately Kubernetes has great support for monitoring. We will use Prometheus and
Grafana to collect and display our load testing metrics.

1. Deploy Prometheus

        $ kubectl apply -f kubernetes-config/prometheus-config.yaml
        $ kubectl apply -f kubernetes-config/prometheus-controller.yaml

2. Deploy Grafana

        $ kubectl apply -f kubernetes-config/grafana-config.yaml
        $ kubectl apply -f kubernetes-config/grafana-controller.yaml

### Configure Ingress

Now that we have our services configured we need to access them. This ingress config will set up a layer-7 load balancer
based on sub-domain. We will also set up Identity Aware Proxy (IAP) to further secure our application.

1. Deploy the ingress config:

        $ kubectl apply -f kubernetes-config/loadtest-ingress.yaml

2. Follow the instructions for [Setting up IAP
   Access](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#iap-access)

At this point you will need to wait for the managed SSL certificate to provision and for the health checks to complete.
This can take about 10-15 minutes.

You can check the status of the certificate with the following command:

        $ kubectl describe managedcertificate loadtest-cert

When the state changes from 'Provisioning' to 'Active' your https is configured

You can check the status of your load balancer ingress with the following command:

        $ kubectl describe ingress loadtest-ingress

In the annotations section you will be able to see the status of the health checks for each backend service. Once they
all read 'HEALTHY' you are ready to go.

Note that IAP may take a few more minutes to set up authentication, even after https and routing are configured.

## Running and Monitoring a Test


The locust interface is now available at `https://locust.loadtest.[DOMAIN]`. The Locust master web interface enables you to execute the load testing tasks against the
system under test.

To begin, specify the total number of users to simulate and a rate at which each user should be spawned. Next, click
Start swarming to begin the simulation. To stop the simulation, click **Stop** and the test will terminate. The
aggregated results can be downloaded into a spreadsheet. Note that the Host parameter (by default set to 'dashboard' in the example
test) is not used when we're working with real browsers - it's used for standard API-based load tests.

[Optional] Scaling clients Scaling up the number of simulated users will require an increase in the number of Locust
worker pods. To increase the number of pods deployed by the deployment, Kubernetes offers the ability to resize
deployments without redeploying them. For example, the following command scales the pool of Locust worker pods to 20:

        $ kubectl scale deployment/lw-pod --replicas=20


### Grafana
Grafana can be accessed at `https://grafana.loadtest.[DOMAIN]`. A dashboard called 'Locust' is preconfigured to connect to your Locust metrics. You can find it by navigating to Dashboards ->
Manage. Kick off a load test from the Locust interface and enjoy your improved metrics dashboard!

### Prometheus
Prometheus can be accessed at `https://prometheus.loadtest.[DOMAIN]`. You can use [PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/) and the API to write queries
against the time series data and extract it.

## Cleaning up

Once you are done load testing and exporting data you can tear down your cluster to avoid additional costs.

    $ gcloud container clusters delete $CLUSTER --zone $ZONE

Note that this leaves your Static IP and OAuth configurations intact and ready to use for the next test. If you so
choose you can delete them too, but you'll need to recreate them the next time you load test and update your DNS to use
your new IP address.


## Additional Reading

1. [Locust Documentation](https://docs.locust.io/en/0.14.6/)
2. [Managed Certificates GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs)
3. [IAP with GKE](https://cloud.google.com/iap/docs/enabling-kubernetes-howto#oauth-configure)
