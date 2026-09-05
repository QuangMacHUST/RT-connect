import pytest
from fastapi.testclient import TestClient

from rt_connect_api.core.config import Settings
from rt_connect_api.main import create_app


@pytest.fixture
def client() -> TestClient:
    settings = Settings(app_env="test", app_version="test-version", database_url=None)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
