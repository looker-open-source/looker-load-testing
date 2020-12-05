import tarfile
import tempfile
import time
from pathlib import Path
from google.cloud.devtools import cloudbuild
from google.cloud import storage
from google.api_core.exceptions import NotFound


def get_build_client(credentials=None):
    """Creates and returns a cloud build client. Credentials only needed
    if the Auth environment variable is not set
    """

    client = cloudbuild.CloudBuildClient(credentials=credentials)

    return client


def get_storage_client(credentials=None):
    """Creates and returns a cloud storage client. Credentials only needed
    if the Auth environment variable is not set
    """

    client = storage.Client(credentials=credentials)

    return client


def get_or_create_bucket(bucket_name, storage_client):
    """Returns a cloud storage bucket object. If not found, it will create the bucket"""

    try:
        bucket = storage_client.get_bucket(bucket_name)
    except NotFound:
        bucket = storage_client.create_buicket(bucket_name)

    return bucket


def upload_source(project, storage_client):
    """Uploads data for the docker container to cloud storage.

    This makes the data available for cloud build to use. The bucket used
    is the same default that the gcloud builds submit command uses. Returns
    a tuple of the bucket name and object (blob) name.
    """

    # A timestamp ensures a unique blob name
    timestamp = int(time.time())
    bucket_name = f"{project}_cloudbuild"
    blob_name = f"source/loadtest-source-{timestamp}.tgz"
    bucket = get_or_create_bucket(bucket_name, storage_client)
    blob = bucket.blob(blob_name)

    root_dir = Path(__file__).parent.parent.resolve()
    source_dir = root_dir.joinpath("docker-image")

    # Creates the tgz file in a temp directory so it auto-deletes
    with tempfile.TemporaryDirectory() as d:
        source_tar = Path(d).joinpath("source.tgz")
        with tarfile.open(source_tar, "w:gz") as tar:
            tar.add(source_dir, arcname=".")

        blob.upload_from_filename(source_tar)

    return (bucket_name, blob_name)


def build_test_image(name, project, image_tag, bucket, blob, build_client):
    """Creates the docker image used for the load test using cloud build. Once built,
    the image is then uploaded to the GCP project's container registry. Returns the
    job ID of the submitted operation which can be used to poll for job status.
    """

    # https://googleapis.dev/python/cloudbuild/latest/cloudbuild_v1/types.html
    # https://cloud.google.com/cloud-build/docs/api/reference/rest/v1/projects.builds
    build = {
        "source": {
            "storage_source": {
                "bucket": bucket,
                "object_": blob
            }
        },
        "images": [f"gcr.io/{project}/{name}:{image_tag}"],
        "steps": [
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": [
                    "build",
                    "--network",
                    "cloudbuild",
                    "--no-cache",
                    "-t",
                    f"gcr.io/{project}/{name}:{image_tag}",
                    "."
                ]
            }
        ]
    }

    request = cloudbuild.CreateBuildRequest(project_id=project, build=build)
    task = build_client.create_build(request=request)

    return task.metadata.build.id


def build_status(build_id, project, build_client):
    """Gets and returns the status of a current build. To be used in a polling loop. Will return
    'SUCCESS' upon a successful build.
    """
    request = cloudbuild.GetBuildRequest(project_id=project, id=build_id)
    build = build_client.get_build(request=request)

    # Typical values are QUEUED, WORKING, and SUCCESS
    return build.status.name
