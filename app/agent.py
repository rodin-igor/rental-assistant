"""Request and output models; agent integration is not implemented yet."""

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Fields users will be able to review and edit."""

    city: str | None = None
    state: str | None = None
    neighborhood: str | None = None
    bedrooms: int | None = None
    max_monthly_rent: float | None = None
    dogs_allowed: bool | None = None
    cats_allowed: bool | None = None
    amenities: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """A rental request and the filters currently shown on the page."""

    message: str
    filters: SearchFilters = Field(default_factory=SearchFilters)


class Listing(BaseModel):
    """Property information displayed in a result card."""

    id: str
    title: str
    description: str
    city: str
    state: str
    neighborhood: str | None = None
    monthly_rent: float
    bedrooms: int
    dogs_allowed: bool | None = None
    cats_allowed: bool | None = None
    amenities: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None


class SearchResponse(BaseModel):
    """Reply, interpreted filters, and matching property cards."""

    message: str
    filters: SearchFilters
    listings: list[Listing] = Field(default_factory=list)
    clarification_question: str | None = None
