import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

from app.config import Settings

# Tests must never pick up a developer's local .env (real keys, demo modes).
Settings.model_config["env_file"] = None
from app.main import create_app  # noqa: E402 - needs the env_file override above

DEMO_PASSWORD = "test-demo-password"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        demo_password=DEMO_PASSWORD,  # type: ignore[arg-type]
        cookie_secure=False,
        login_max_failures=3,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def emma(client: TestClient) -> TestClient:
    login(client, "emma")
    return client
