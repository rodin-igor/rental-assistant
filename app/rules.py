"""Plain-Python rental search rules."""

from typing import Any


def has_complete_location(
    city: str | None, state: str | None, neighborhood: str | None = None
) -> bool:
    """Require nonblank city and state, regardless of neighborhood.

    This checks completeness only, without validating geographic names.
    """
    return bool(city and city.strip() and state and state.strip())


def merge_filter_changes(
    current: dict[str, Any], changes: dict[str, Any]
) -> dict[str, Any]:
    """Keep untouched requirements while honoring explicit removals."""
    result = current | changes
    if "amenities" in result and result["amenities"] is None:
        result["amenities"] = []
    return result


def location_question(city: str | None, state: str | None) -> str | None:
    """Identify missing location text without validating geographic names."""
    if has_complete_location(city, state):
        return None
    missing = []
    if not city or not city.strip():
        missing.append("city")
    if not state or not state.strip():
        missing.append("state")
    return f"Please provide the {' and '.join(missing)} for your rental search."
