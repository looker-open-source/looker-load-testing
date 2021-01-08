import tarfile
from pathlib import Path
from nuke_from_orbit.utils import cloud_build
from google.cloud.devtools import cloudbuild
from google.cloud import storage
from google.api_core.exceptions import NotFound


ROOT_DIR = Path(__file__).parent.parent.joinpath("nuke_from_orbit/")


class MockBucket:
    def __init__(self, name):
        self.name = name

    @staticmethod
    def blob(blob_name):
        return MockBlob()


class MockBlob:
    @staticmethod
    def upload_from_filename(filename):
        return filename


class MockStorageClient:
    @staticmethod
    def get_bucket():
        pass

    @staticmethod
    def create_bucket():
        pass


class MockBuildClient:
    @staticmethod
    def create_build():
        pass

    @staticmethod
    def get_build():
        pass


def test_get_build_client(mocker):
    mocker.patch("google.cloud.devtools.cloudbuild.CloudBuildClient")
    cloudbuild.CloudBuildClient.return_value = "foo"
    client = cloud_build.get_build_client()
    assert client == "foo"


def test_get_storage_client(mocker):
    mocker.patch("google.cloud.storage.Client")
    storage.Client.return_value = "bar"
    client = cloud_build.get_storage_client()
    assert client == "bar"


def test_get_or_create_bucket_exists(mocker):
    mock_storage_client = MockStorageClient()
    mocker.patch.object(mock_storage_client, "get_bucket")
    mock_storage_client.get_bucket.return_value = MockBucket(name="foo")
    bucket = cloud_build.get_or_create_bucket("foo", mock_storage_client)
    assert bucket.__dict__ == MockBucket(name="foo").__dict__


def test_get_or_create_bucket_no_exist(mocker):
    mock_storage_client = MockStorageClient()
    mocker.patch.object(mock_storage_client, "get_bucket", side_effect=NotFound("mock message"))
    mocker.patch.object(mock_storage_client, "create_bucket")
    mock_storage_client.create_bucket.return_value = MockBucket(name="bar")

    bucket = cloud_build.get_or_create_bucket("bar", mock_storage_client)
    assert bucket.__dict__ == MockBucket(name="bar").__dict__


def test_upload_source_return(mocker):
    mocker.patch("time.time").return_value = 1234
    mocker.patch("nuke_from_orbit.utils.cloud_build.get_or_create_bucket").return_value = MockBucket(name="foo")
    mocker.patch("tempfile.TemporaryDirectory").return_value.__enter__.return_value = "tempdirname"
    mocker.patch("tarfile.open").return_value.__enter__.return_value.add.return_value = "mocktar"

    resp = cloud_build.upload_source("foo_project", "foo_client")
    assert resp == ("foo_project_cloudbuild", "source/loadtest-source-1234.tgz")


def test_upload_source_tar_add_call(mocker):

    docker_path = ROOT_DIR.joinpath("docker-image").resolve()

    mocker.patch("time.time").return_value = 1234
    mocker.patch("nuke_from_orbit.utils.cloud_build.get_or_create_bucket").return_value = MockBucket(name="foo")
    mocker.patch("tempfile.TemporaryDirectory").return_value.__enter__.return_value = "tempdirname"
    mocker.patch("tarfile.open").return_value.__enter__.return_value.add

    cloud_build.upload_source("foo_project", "foo_client")
    tarfile.open.return_value.__enter__.return_value.add.assert_called_with(docker_path, arcname=".")


def test_upload_source_blob_upload_call(mocker):
    mocker.patch("time.time").return_value = 1234
    mocker.patch("nuke_from_orbit.utils.cloud_build.get_or_create_bucket").return_value = MockBucket(name="foo")
    mocker.patch("tempfile.TemporaryDirectory").return_value.__enter__.return_value = "tempdirname"
    mocker.patch("tarfile.open").return_value.__enter__.return_value.add.return_value = "mocktar"

    mocker.patch.object(MockBlob, "upload_from_filename")

    cloud_build.upload_source("foo_project", "foo_client")
    MockBlob.upload_from_filename.assert_called_with(Path("tempdirname/source.tgz"))


def test_build_test_image(mocker):
    mock_build_client = MockBuildClient()
    mocker.patch.object(mock_build_client, "create_build").return_value.metadata.build.id = "abc123"
    mocker.patch("google.cloud.devtools.cloudbuild.CreateBuildRequest").return_value = "foo"

    task_id = cloud_build.build_test_image("taco", "cat", "v1", "foo_bucket", "foo_blob", mock_build_client)

    assert task_id == "abc123"


def test_build_test_image_request(mocker):
    test_build = {
        "source": {
            "storage_source": {
                "bucket": "foo_bucket",
                "object_": "foo_blob"
            }
        },
        "images": ["gcr.io/cat/taco:v1"],
        "steps": [
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": [
                    "build",
                    "--network",
                    "cloudbuild",
                    "--no-cache",
                    "-t",
                    "gcr.io/cat/taco:v1",
                    "."
                ]
            }
        ]
    }

    mock_build_client = MockBuildClient()
    mocker.patch.object(mock_build_client, "create_build").return_value.metadata.build.id = "abc123"
    mocker.patch("google.cloud.devtools.cloudbuild.CreateBuildRequest")

    cloud_build.build_test_image("taco", "cat", "v1", "foo_bucket", "foo_blob", mock_build_client)
    cloudbuild.CreateBuildRequest.assert_called_with(project_id="cat", build=test_build)


def test_build_status(mocker):
    mock_build_client = MockBuildClient()
    mocker.patch.object(mock_build_client, "get_build").return_value.status.name = "WORKING"
    mocker.patch("google.cloud.devtools.cloudbuild.GetBuildRequest").return_value = "foo"

    status = cloud_build.build_status("abc123", "foo_project", mock_build_client)
    assert status == "WORKING"


def test_build_status_request(mocker):
    mock_build_client = MockBuildClient()
    mocker.patch.object(mock_build_client, "get_build").return_value.status.name = "WORKING"
    mocker.patch("google.cloud.devtools.cloudbuild.GetBuildRequest")

    cloud_build.build_status("abc123", "foo_project", mock_build_client)
    cloudbuild.GetBuildRequest.assert_called_with(project_id="foo_project", id="abc123")
