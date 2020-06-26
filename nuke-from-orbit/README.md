## Introduction

![nuke-from-orbit](https://i.imgflip.com/1o9ejc.jpg)

Sometimes you need a little more boom, so let's rain fire from the clouds... it's the only way to be sure.

This section contains a framework for a Kubernetes-based distributed LocustIO cluster. Provided is an example of how to
run a "real browser" based test of a looker dashboard.

This guide is derived from the official GCP locust/kubernetes tutorial, which can be found
[here.](https://cloud.google.com/solutions/distributed-load-testing-using-gke)

The instructions below are for GCP, but this can be run on any Kubernetes cluster in any environment. At a high level
the steps are:

1. Build a Docker image of your locust tests
2. Spin up a Kubernetes cluster
3. Create the master and worker deployments, the service, and any related secrets
4. Wire it up to a monitoring solution, like Grafana

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
on a dashboard this is equivalent to 600 concurrent users.

## Before you begin

Open Cloud Shell to execute the commands listed in this tutorial.

Define environment variables for the project id, region and zone you want to use for this tutorial.

    $ PROJECT=$(gcloud config get-value project)
    $ REGION=us-central1
    $ ZONE=${REGION}-c
    $ CLUSTER=gke-load-test
    $ gcloud config set compute/region $REGION
    $ gcloud config set compute/zone $ZONE

**Note:** Following services should be enabled in your project: Cloud Build, Kubernetes Engine, Cloud Storage

    $ gcloud services enable \
      cloudbuild.googleapis.com \
      compute.googleapis.com \
      container.googleapis.com \
      containeranalysis.googleapis.com \
      containerregistry.googleapis.com

## Setup

1. Create GKE cluster

        $ gcloud container clusters create $CLUSTER \
          --zone $ZONE \
          --scopes "https://www.googleapis.com/auth/cloud-platform" \
          --num-nodes "3" \
          --machine-type "c2-standard-8" \
          --addons HttpLoadBalancing

        $ gcloud container clusters get-credentials $CLUSTER \
          --zone $ZONE \
          --project $PROJECT

2. Clone repo in a local directory on your cloud shell environment and cd to the `nuke-from-orbit` directory

        $ git clone https://github.com/JCPistell/looker-load-testing.git
        $ cd looker-load-testing/nuke-from-orbit

3. **Very Important!** Modify the contents of `docker-image/locust-tasks/tasks.py` to suit your testing criteria

> The example `tasks.py` outlines a standard dashboard rendering performance test. Near the top of the file you will
> want to modify the `SITE` and `DASH_ID` variables to match the Looker instance you are testing and the relevant
> dashboard id. Different testing goals will require specific test code - Locust is flexible enough to handle just about
> any kind of test you can think of!

4. Build docker image and store it in your project's container registry. Note this command assumes you are in the
   `nuke-from-orbit` directory.

        $ gcloud builds submit --tag gcr.io/$PROJECT/locust-tasks:latest docker-image/.

5. Replace [PROJECT_ID] in locust-controller.yaml with the deployed endpoint and project-id respectively.

        $ sed -i -e "s/\[PROJECT_ID\]/$PROJECT/g" kubernetes-config/locust-controller.yaml

   If you want to enable step-mode you can change the `LOCUST_STEP` variables from `"false"` to `"true"` in
   `locust-controller.yaml` - note that you must do this in both the `lm-pod` and `lw-pod` Deployments.

6. Create a Kubernetes secret called `website-creds` that contains two entries - `username` and `password` - that tie to
   the Looker instance you will be logging into (the instance you specified in step 3):

        $ echo -n <your username> > username.txt
        $ echo -n <your password> > pass.txt
        $ kubectl create secret generic website-creds --from-file=username=./username.txt --from-file=password=./pass.txt

7. Deploy Locust master and worker nodes:

        $ kubectl apply -f kubernetes-config/locust-controller.yaml

8. Get the external IP of Locust master service. Note this may take a minute or two to populate so we will use a `watch`
   command to know when it's ready:

        $ watch kubectl get svc

    When the IP address is ready, copy it for the next step.

9. Starting load testing. The Locust master web interface enables you to execute the load testing tasks against the
   system under test. Access the URL as http://[YOUR LOCUST IP]:8089.

To begin, specify the total number of users to simulate and a rate at which each user should be spawned. Next, click
Start swarming to begin the simulation. To stop the simulation, click **Stop** and the test will terminate. The complete
results can be downloaded into a spreadsheet. Note that the Host parameter (by default set to 'dashboard' in the example
test) is not used when we're working with real browsers - it's used for standard API-based load tests.

10. [Optional] Scaling clients Scaling up the number of simulated users will require an increase in the number of Locust
   worker pods. To increase the number of pods deployed by the deployment, Kubernetes offers the ability to resize
   deployments without redeploying them. For example, the following command scales the pool of Locust worker pods to 20:

        $ kubectl scale deployment/lw-pod --replicas=20

## [Optional] Better Monitoring and Data Retention

While we can now load test Looker at scale the data available from locust out of the box leaves something to be desired.
Summary metrics are available for download, but the rich timeseries data is not, and the charts reset on every refresh.
We can probably do better, and fortunately Kubernetes has great support for monitoring. We will use Prometheus and
Grafana to collect and display our load testing metrics.

1. Deploy Prometheus

        $ kubectl apply -f kubernetes-config/prometheus-config.yaml
        $ kubectl apply -f kubernetes-config/prometheus-controller.yaml

4. Deploy Grafana

        $ kubectl apply -f kubernetes-config/grafana-config.yaml
        $ kubectl apply -f kubernetes-config/grafana-controller.yaml

5. Get the external IP of the Grafana service (this make take a minute to be available):

        $ watch kubectl get svc

6. Navigate to the IP address on port 3000 (e.g. http://[YOUR GRAFANA IP]:3000) and log in - the default username/password is
   `admin/admin`. You will be prompted to change it on your first login

7. A dashboard should be preconfigured to connect to your Locust metrics. You can find it by navigating to Dashboards ->
   Manage. Kick off a load test from the Locust interface and enjoy your improved metrics dashboard!

## Cleaning up

    $ gcloud container clusters delete $CLUSTER --zone $ZONE
