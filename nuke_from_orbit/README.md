## Distribute Load Testing Using GKE

## Introduction

!(nuke_from_orbit)[https://gfycat.com/farfavoriteconey]

A kubernetes-based distributed locustio cluster. Provided is an example of how to run a "real browser" based test of a
looker dashboard.

The instructions below are for GCP, but this can be run on any Kubernetes cluster in any environment.


## Before you begin

Open Cloud Shell to execute the commands listed in this tutorial.

Define environment variables for the project id, region and zone you want to use for this tutorial.

    $ PROJECT=$(gcloud config get-value project)
    $ REGION=us-central1
    $ ZONE=${REGION}-b
    $ CLUSTER=gke-load-test
    $ TARGET=${PROJECT}.appspot.com
    $ gcloud config set compute/region $REGION 
    $ gcloud config set compute/zone $ZONE

**Note:** Following services should be enabled in your project:
Cloud Build
Kubernetes Engine
Google App Engine Admin API 
Cloud Storage

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
                --enable-autoscaling --min-nodes "3" \
                --max-nodes "10" \
                --addons HorizontalPodAutoscaling,HttpLoadBalancing

        $ gcloud container clusters get-credentials $CLUSTER \
        --zone $ZONE \
        --project $PROJECT

2. Clone tutorial repo in a local directory on your cloud shell environment

        $ git clone <this-repository>

3. Build docker image and store it in your project's container registry

        $ pushd gke-load-test
        $ gcloud builds submit --tag gcr.io/$PROJECT/locust-tasks:latest docker-image/.

4. Deploy sample application on GAE

        $ gcloud app deploy sample-webapp/app.yaml --project=$PROJECT

5. Replace [TARGET_HOST] and [PROJECT_ID] in locust-master-controller.yaml and locust-worker-controller.yaml with the deployed endpoint and project-id respectively. 

        $ sed -i -e "s/\[TARGET_HOST\]/$TARGET/g" kubernetes-config/locust-master-controller.yaml
        $ sed -i -e "s/\[TARGET_HOST\]/$TARGET/g" kubernetes-config/locust-worker-controller.yaml
        $ sed -i -e "s/\[PROJECT_ID\]/$PROJECT/g" kubernetes-config/locust-master-controller.yaml
        $ sed -i -e "s/\[PROJECT_ID\]/$PROJECT/g" kubernetes-config/locust-worker-controller.yaml

6. Deploy Locust master and worker nodes:

        $ kubectl apply -f kubernetes-config/locust-master-controller.yaml
        $ kubectl apply -f kubernetes-config/locust-master-service.yaml
        $ kubectl apply -f kubernetes-config/locust-worker-controller.yaml

7. Get the external ip of Locust master service 

        $ EXTERNAL_IP=$(kubectl get svc locust-master -o yaml | grep ip | awk -F":" '{print $NF}')

8. Starting load testing
The Locust master web interface enables you to execute the load testing tasks against the system under test, as shown in the following image. Access the url as http://$EXTERNAL_IP:8089.

To begin, specify the total number of users to simulate and a rate at which each user should be spawned. Next, click Start swarming to begin the simulation. To stop the simulation, click **Stop** and the test will terminate. The complete results can be downloaded into a spreadsheet. 

9. [Optional] Scaling clients
Scaling up the number of simulated users will require an increase in the number of Locust worker pods. To increase the number of pods deployed by the deployment, Kubernetes offers the ability to resize deployments without redeploying them. For example, the following command scales the pool of Locust worker pods to 20:

        $ kubectl scale deployment/locust-worker --replicas=20

## Cleaning up

    $ gcloud container clusters delete $CLUSTER --zone $ZONE
