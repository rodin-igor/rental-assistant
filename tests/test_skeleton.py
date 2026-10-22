"""Minimal checks for the page and search response contract."""

from html.parser import HTMLParser

from fastapi.testclient import TestClient
from pydantic_ai.models import override_allow_model_requests

from app.main import app


class SearchFormParser(HTMLParser):
    """Find the search form without depending on its markup or contents."""

    def __init__(self) -> None:
        super().__init__()
        self.has_search_form = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "form" and dict(attrs).get("id") == "search-form":
            self.has_search_form = True


def test_home_contains_search_form() -> None:
    with override_allow_model_requests(False), TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    parser = SearchFormParser()
    parser.feed(response.text)
    assert parser.has_search_form


def test_search_returns_declared_top_level_fields() -> None:
    with override_allow_model_requests(False), TestClient(app) as client:
        response = client.post(
            "/search",
            json={
                "message": "Find a two-bedroom apartment in Honolulu, HI.",
                "filters": {"city": "Honolulu", "state": "HI", "bedrooms": 2},
            },
        )

    assert response.status_code == 200
    assert set(response.json()) == {
        "message",
        "filters",
        "listings",
        "clarification_question",
    }
