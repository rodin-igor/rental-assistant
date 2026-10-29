"""Keep every automated test disconnected from real models."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models import override_allow_model_requests
from pydantic_ai.models.test import TestModel

from app.agent import model_dependency
from app.main import app


@pytest.fixture(autouse=True)
def deny_real_model_requests() -> Iterator[None]:
    with override_allow_model_requests(False):
        yield


@pytest.fixture
def test_model() -> TestModel:
    return TestModel(custom_output_args={"message": "Filters updated.", "changes": {}})


@pytest.fixture
def client(test_model: TestModel) -> Iterator[TestClient]:
    app.dependency_overrides[model_dependency] = lambda: test_model
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
