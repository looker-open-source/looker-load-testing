import tarfile
import tempfile
import time
from pathlib import Path
from google.cloud.devtools import cloudbuild
from google.cloud import storage
from google.api_core.exceptions import NotFound


def get_build_client(credentials):
    client = cloudbuild.CloudBuildClient(credentials=credentials)

    return client


def get_storage_client(credentials):
    client = storage.Client(credentials=credentials)

    return client


def get_or_create_bucket(bucket_name, storage_client):

    try:
        bucket = storage_client.get_bucket(bucket_name)
    except NotFound:
        bucket = storage_client.create_buicket(bucket_name)

    return bucket


def upload_source(project, storage_client):
    timestamp = int(time.time())
    bucket_name = f"{project}_cloudbuild"
    blob_name = f"source/loadtest-source-{timestamp}.tgz"
    bucket = get_or_create_bucket(bucket_name, storage_client)
    blob = bucket.blob(blob_name)

    root_dir = Path(__file__).parent.parent.resolve()
    source_dir = root_dir.joinpath("docker-image")

    with tempfile.TemporaryDirectory() as d:
        source_tar = Path(d).joinpath("source.tgz")
        with tarfile.open(source_tar, "w:gz") as tar:
            tar.add(source_dir, arcname=".")

        blob.upload_from_filename(source_tar)

    return (bucket_name, blob_name)


def build_test_image(name, project, image_tag, bucket, blob, build_client):

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
    request = cloudbuild.GetBuildRequest(project_id=project, id=build_id)
    build = build_client.get_build(request=request)

    return build.status.name
