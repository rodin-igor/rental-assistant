"""Request-level behavior through real routes, rules, and a TestModel agent."""

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.test import TestModel

from app.agent import model_dependency
from app.main import app


def test_budget_follow_up_preserves_other_requirements(
    client: TestClient, test_model: TestModel
) -> None:
    test_model.custom_output_args = {
        "message": "Budget updated.", "changes": {"max_monthly_rent": 2200}
    }

    response = client.post("/search", json={
        "message": "Lower my budget to $2,200.",
        "filters": {
            "city": "Honolulu", "state": "HI", "bedrooms": 2,
            "max_monthly_rent": 2500, "dogs_allowed": True, "amenities": ["parking"],
        },
    })

    assert response.status_code == 200
    body = response.json()
    assert body["filters"] == {
        "city": "Honolulu", "state": "HI", "neighborhood": None, "bedrooms": 2,
        "max_monthly_rent": 2200, "dogs_allowed": True,
        "cats_allowed": None, "amenities": ["parking"],
    }
    assert body["clarification_question"] is None
    assert body["listings"] == []


def test_explicit_budget_removal_is_applied(client: TestClient, test_model: TestModel) -> None:
    test_model.custom_output_args = {
        "message": "Budget removed.", "changes": {"max_monthly_rent": None}
    }

    response = client.post("/search", json={
        "message": "Remove my budget limit.",
        "filters": {"city": "Honolulu", "state": "HI", "max_monthly_rent": 2500},
    })

    assert response.status_code == 200
    assert response.json()["filters"]["max_monthly_rent"] is None


def test_neighborhood_request_keeps_draft_until_location_is_supplied(
    client: TestClient, test_model: TestModel
) -> None:
    test_model.custom_output_args = {
        "message": "I need a location.",
        "changes": {"bedrooms": 2, "neighborhood": "Downtown", "dogs_allowed": True},
    }

    first = client.post("/search", json={"message": "Two bedrooms in Downtown, dogs allowed."})

    assert first.status_code == 200
    draft = first.json()
    assert draft["clarification_question"]
    assert draft["filters"]["city"] is None
    test_model.custom_output_args = {
        "message": "Location completed.", "changes": {"city": "Honolulu", "state": "HI"}
    }
    second = client.post("/search", json={
        "message": "Honolulu, HI.",
        "draft_filters": draft["filters"],
        "clarification_question": draft["clarification_question"],
    })

    assert second.status_code == 200
    body = second.json()
    assert body["clarification_question"] is None
    assert body["filters"]["bedrooms"] == 2
    assert body["filters"]["neighborhood"] == "Downtown"
    assert body["filters"]["dogs_allowed"] is True


def test_unrelated_message_cannot_change_filters_or_clear_a_pending_question(
    client: TestClient, test_model: TestModel
) -> None:
    test_model.custom_output_args = {
        "message": "This app helps with rentals.",
        "relevant": False, "changes": {"city": "Seattle", "max_monthly_rent": None},
    }

    response = client.post("/search", json={
        "message": "What is the capital of France?",
        "filters": {"city": "Honolulu", "state": "HI", "max_monthly_rent": 2500},
        "draft_filters": {"city": "Honolulu", "state": "HI", "bedrooms": 2},
        "clarification_question": "What budget do you mean by cheap?",
    })

    assert response.status_code == 200
    assert response.json()["filters"]["city"] == "Honolulu"
    assert response.json()["filters"]["bedrooms"] == 2
    assert response.json()["clarification_question"] == "What budget do you mean by cheap?"


def test_model_ambiguity_stages_a_complete_location(client: TestClient, test_model: TestModel) -> None:
    test_model.custom_output_args = {
        "message": "Please clarify cheap.", "changes": {"amenities": ["parking"]},
        "clarification_question": "What maximum monthly rent do you mean?",
    }

    response = client.post("/search", json={
        "message": "Somewhere cheap with parking.",
        "filters": {"city": "Honolulu", "state": "HI"},
    })

    assert response.status_code == 200
    assert response.json()["clarification_question"]
    assert response.json()["filters"]["amenities"] == ["parking"]


@pytest.mark.parametrize("complete", [True, False])
def test_manual_apply_works_without_gateway_configuration_or_a_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, complete: bool
) -> None:
    app.dependency_overrides.clear()
    monkeypatch.delenv("LLM_API_GATEWAY", raising=False)
    monkeypatch.delenv("LLM_API_TOKEN", raising=False)
    filters = {"bedrooms": 2, "neighborhood": "Downtown"}
    if complete:
        filters.update(city="Honolulu", state="HI")

    response = client.post("/filters/apply", json={"filters": filters})

    assert response.status_code == 200
    assert response.json()["filters"]["bedrooms"] == 2
    assert bool(response.json()["clarification_question"]) is not complete
    assert response.json()["listings"] == []


def test_empty_chat_does_not_reach_the_model(client: TestClient, test_model: TestModel) -> None:
    response = client.post("/search", json={"message": "  "})

    assert response.status_code == 422
    assert test_model.last_model_request_parameters is None


@pytest.mark.parametrize("status", [401, 429, 503])
def test_upstream_failure_is_safe_and_not_retried(client: TestClient, status: int) -> None:
    class FailingModel(TestModel):
        attempts = 0

        async def request(self, messages, model_settings, model_request_parameters):
            self.attempts += 1
            raise ModelHTTPError(status, "test", body={"private": "provider-secret"})

    failing = FailingModel()
    app.dependency_overrides[model_dependency] = lambda: failing

    response = client.post("/search", json={"message": "Find an apartment."})

    assert response.status_code == 503
    assert "provider-secret" not in response.text
    assert failing.attempts == 1


def test_invalid_model_output_returns_safe_error(client: TestClient, test_model: TestModel) -> None:
    test_model.custom_output_args = {
        "message": "Bad output.", "changes": {"bedrooms": "not-a-number"}
    }

    response = client.post("/search", json={"message": "Find an apartment."})

    assert response.status_code == 503
    assert "not-a-number" not in response.text


def test_missing_configuration_does_not_break_home_or_expose_settings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.dependency_overrides.clear()
    monkeypatch.delenv("LLM_API_TOKEN", raising=False)

    assert client.get("/").status_code == 200
    response = client.post("/search", json={"message": "Find an apartment."})
    assert response.status_code == 503
