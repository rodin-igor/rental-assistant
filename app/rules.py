"""Plain-Python rental search rules."""


def has_complete_location(
    city: str | None, state: str | None, neighborhood: str | None = None
) -> bool:
    """Require nonblank city and state, regardless of neighborhood.

    This checks completeness only, without validating geographic names.
    """
    return bool(city and city.strip() and state and state.strip())
