"""Routes and a minimal page for the rental assistant prototype."""

from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_ai.models import Model

from app.agent import (
    AgentUnavailableError,
    ApplyRequest,
    SearchRequest,
    SearchResponse,
    model_dependency,
)
from app.service import apply_filters, interpret_search

load_dotenv()

app = FastAPI(title="Rental Assistant")

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rental Assistant</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem auto;
           padding: 0 1rem; max-width: 64rem; color: #243044; }
    .layout { display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; }
    section, aside { border: 1px solid #ccd3dd; border-radius: .5rem;
                     padding: 1rem; margin-bottom: 1rem; }
    label { display: block; margin-top: .75rem; }
    input, select, textarea, button { font: inherit; }
    input, select, textarea { box-sizing: border-box; width: 100%; padding: .5rem; }
    button { margin-top: .75rem; padding: .5rem 1rem; }
    article { border-top: 1px solid #ccd3dd; padding: .75rem 0; }
    #reply, #original-prompt { white-space: pre-wrap; }
    @media (max-width: 40rem) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>Rental Assistant</h1>
  <p>Prototype: every submission returns the same sample listing and filters.</p>
  <div class="layout">
    <aside aria-label="Search filters">
      <details>
        <summary>Editable filters</summary>
        <p>Filter changes are not applied in this prototype.</p>
        <label for="city">City</label><input id="city">
        <label for="state">State</label><input id="state">
        <label for="neighborhood">Neighborhood</label><input id="neighborhood">
        <label for="bedrooms">Bedrooms</label>
        <input id="bedrooms" type="number" step="1">
        <label for="max_monthly_rent">Maximum monthly rent ($)</label>
        <input id="max_monthly_rent" type="number" step="any">
        <label for="dogs_allowed">Dogs allowed</label>
        <select id="dogs_allowed">
          <option value="">Unspecified</option>
          <option value="true">Yes</option><option value="false">No</option>
        </select>
        <label for="cats_allowed">Cats allowed</label>
        <select id="cats_allowed">
          <option value="">Unspecified</option>
          <option value="true">Yes</option><option value="false">No</option>
        </select>
        <label for="amenities">Amenities (comma-separated)</label>
        <input id="amenities">
        <button type="button" disabled>Apply filters (coming later)</button>
      </details>
    </aside>
    <main>
      <section aria-labelledby="chat-heading">
        <h2 id="chat-heading">Chat</h2>
        <form id="search-form" action="/search" method="post">
          <label for="message">Describe your rental needs</label>
          <textarea id="message" name="message" rows="3" required></textarea>
          <button id="submit" type="submit">Send</button>
        </form>
        <p id="original-prompt"></p>
        <p id="reply" role="status" aria-live="polite"></p>
      </section>
      <section aria-labelledby="results-heading">
        <h2 id="results-heading">Results</h2>
        <div id="results">Submit a request to see the placeholder response.</div>
      </section>
      <section aria-labelledby="liked-heading">
        <h2 id="liked-heading">Liked</h2>
        <p>No liked listings. Liking will be available in a future version.</p>
      </section>
    </main>
  </div>
  <script>
    const textFields = ['city', 'state', 'neighborhood'];
    const numberFields = ['bedrooms', 'max_monthly_rent'];
    const petFields = ['dogs_allowed', 'cats_allowed'];
    const field = (id) => document.getElementById(id);

    function readFilters() {
      const filters = {};
      for (const key of textFields) filters[key] = field(key).value || null;
      for (const key of numberFields) {
        filters[key] = field(key).value === '' ? null : Number(field(key).value);
      }
      for (const key of petFields) {
        filters[key] = field(key).value === '' ? null : field(key).value === 'true';
      }
      filters.amenities = field('amenities').value.split(',')
        .map((item) => item.trim()).filter(Boolean);
      return filters;
    }

    function displayResponse(data) {
      field('reply').textContent = data.message;
      for (const key of [...textFields, ...numberFields, ...petFields]) {
        field(key).value = data.filters[key] ?? '';
      }
      field('amenities').value = data.filters.amenities.join(', ');
      field('results').replaceChildren();
      for (const listing of data.listings) {
        const card = document.createElement('article');
        const title = document.createElement('h3');
        title.textContent = listing.title;
        const details = document.createElement('p');
        details.textContent = `${listing.city}, ${listing.state} · `
          + `${listing.bedrooms} bedrooms · $${listing.monthly_rent}/month`;
        const description = document.createElement('p');
        description.textContent = listing.description;
        const amenities = document.createElement('p');
        amenities.textContent = 'Amenities: ' + listing.amenities.join(', ');
        const like = document.createElement('button');
        like.type = 'button';
        like.disabled = true;
        like.textContent = 'Like (coming later)';
        card.append(title, details, description, amenities, like);
        field('results').append(card);
      }
    }

    field('search-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = field('message').value;
      field('original-prompt').textContent = 'Your request: ' + message;
      field('reply').textContent = 'Loading placeholder response…';
      field('submit').disabled = true;
      try {
        const response = await fetch('/search', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message, filters: readFilters()}),
        });
        if (!response.ok) throw new Error('Request failed. Please try again.');
        displayResponse(await response.json());
      } catch (error) {
        field('reply').textContent = error.message;
      } finally {
        field('submit').disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """Show the prototype page."""
    return PAGE


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest, model: Annotated[Model, Depends(model_dependency)]
) -> SearchResponse:
    """Interpret a new message using the supplied history and current state."""
    return await interpret_search(request, model)


@app.post("/filters/apply", response_model=SearchResponse)
def apply(request: ApplyRequest) -> SearchResponse:
    """Accept direct edits without model access."""
    return apply_filters(request)


@app.exception_handler(AgentUnavailableError)
async def agent_error(request: Request, error: AgentUnavailableError) -> JSONResponse:
    """Return only application-authored errors, never raw provider details."""
    return JSONResponse(status_code=503, content={"detail": str(error)})
