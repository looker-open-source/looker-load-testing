from nuke_from_orbit.utils import cloud_build
from google.cloud.devtools import cloudbuild
from google.cloud import storage
from google.api_core.exceptions import NotFound


class MockBucket:
    def __init__(self, name):
        self.name = name

    @staticmethod
    def blob():
        pass


class MockBlob:
    pass


class MockStorageClient:
    @staticmethod
    def get_bucket():
        pass

    @staticmethod
    def create_bucket():
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
