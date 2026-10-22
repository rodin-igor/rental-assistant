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
