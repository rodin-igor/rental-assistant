"""Complete-location contract from proposal acceptance criterion 3."""

import pytest

from app import rules


@pytest.mark.parametrize(
    ("city", "state"),
    [
        ("Honolulu", "HI"),
        (" Honolulu ", " HI "),
        ("\tHonolulu\n", "\tHI\n"),
        ("Example City", "Example State"),
    ],
)
def test_complete_location_accepts_non_whitespace_text(city: str, state: str) -> None:
    assert rules.has_complete_location(city=city, state=state) is True


@pytest.mark.parametrize("missing_value", [None, "", "   ", "\t\n"])
@pytest.mark.parametrize("missing_field", ["city", "state"])
def test_complete_location_rejects_missing_city_or_state(
    missing_field: str, missing_value: str | None
) -> None:
    location = {"city": "Honolulu", "state": "HI"}
    city = missing_value if missing_field == "city" else location["city"]
    state = missing_value if missing_field == "state" else location["state"]

    assert rules.has_complete_location(
        city=city, state=state, neighborhood="Downtown"
    ) is False


def test_neighborhood_alone_is_not_a_complete_location() -> None:
    assert rules.has_complete_location(
        city=None, state=None, neighborhood="Downtown"
    ) is False


def test_merge_changes_preserves_untouched_fields_and_explicit_false() -> None:
    current = {"city": "Honolulu", "max_monthly_rent": 2500, "dogs_allowed": True}

    result = rules.merge_filter_changes(current, {"max_monthly_rent": 2200, "dogs_allowed": False})

    assert result == {"city": "Honolulu", "max_monthly_rent": 2200, "dogs_allowed": False}
    assert current == {"city": "Honolulu", "max_monthly_rent": 2500, "dogs_allowed": True}


def test_explicit_null_removes_budget_and_clears_amenities() -> None:
    result = rules.merge_filter_changes(
        {"max_monthly_rent": 2500, "amenities": ["parking"]},
        {"max_monthly_rent": None, "amenities": None},
    )

    assert result == {"max_monthly_rent": None, "amenities": []}


@pytest.mark.parametrize(("city", "state"), [(None, None), (" ", "HI"), ("Honolulu", "")])
def test_incomplete_location_requires_a_question(city: str | None, state: str | None) -> None:
    assert rules.location_question(city, state)


def test_complete_location_requires_no_question() -> None:
    assert rules.location_question(" Honolulu ", " HI ") is None
