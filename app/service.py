"""Coordinate interpretation and plain rules without putting decisions in routes."""

from openai import APIError
from pydantic_ai.exceptions import AgentRunError, ModelHTTPError
from pydantic_ai.models import Model

from app.agent import (
    AgentUnavailableError,
    ApplyRequest,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    interpret,
)
from app.rules import location_question, merge_filter_changes


def apply_filters(request: ApplyRequest) -> SearchResponse:
    """Validate a direct snapshot without asking a model to interpret it."""
    question = location_question(request.filters.city, request.filters.state)
    return SearchResponse(
        message="Complete the location to apply these filters." if question else "Filters applied.",
        filters=request.filters,
        clarification_question=question,
    )


async def interpret_search(request: SearchRequest, model: Model) -> SearchResponse:
    """Apply only relevant field changes, retaining incomplete candidates as drafts."""
    try:
        result = await interpret(request, model)
    except ModelHTTPError as error:
        raise AgentUnavailableError(_gateway_error_message(error.status_code)) from None
    except (AgentRunError, APIError, TimeoutError):
        raise AgentUnavailableError(
            "Chat could not process that request. Your filters are unchanged; please try again."
        ) from None

    current = request.draft_filters or request.filters
    if not result.relevant:
        return SearchResponse(
            message="I can help with rental search requirements. Tell me what you need in a rental.",
            filters=current,
            clarification_question=request.clarification_question,
        )
    changes = result.changes.model_dump(exclude_unset=True)
    candidate = SearchFilters.model_validate(
        merge_filter_changes(current.model_dump(), changes)
    )
    question = location_question(candidate.city, candidate.state)
    question = question or (result.clarification_question or "").strip() or None
    return SearchResponse(
        message=result.message,
        filters=candidate,
        clarification_question=question,
    )


def _gateway_error_message(status_code: int) -> str:
    if status_code == 401:
        return "Gateway authentication failed. Check the server API token before trying again."
    if status_code == 429:
        return "The gateway budget is exhausted. Ask your instructor before trying again."
    return "The model is unavailable. Your filters are unchanged; please try again later."
