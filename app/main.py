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

PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rental Assistant</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 2rem auto; padding: 0 1rem;
           max-width: 68rem; color: #243044; background: #f7f9fc; line-height: 1.5; }
    h1 { margin-bottom: .25rem; }
    h2 { margin-top: 0; }
    .layout { display: grid; grid-template-columns: minmax(15rem, 1fr) 2fr; gap: 1rem; }
    section, aside { border: 1px solid #ccd3dd; border-radius: .6rem; background: white;
                     padding: 1.1rem; margin-bottom: 1rem; }
    label { display: block; margin-top: .75rem; font-weight: 600; }
    input, select, textarea, button { font: inherit; }
    input, select, textarea { width: 100%; padding: .5rem; border: 1px solid #9baabc;
                             border-radius: .3rem; color: inherit; background: white; }
    textarea { resize: vertical; }
    button { margin-top: .75rem; padding: .5rem 1rem; border-radius: .3rem;
             border: 1px solid #24476f; background: #24476f; color: white; cursor: pointer; }
    button:disabled { opacity: .6; cursor: wait; }
    :focus-visible { outline: 3px solid #d59a32; outline-offset: 2px; }
    fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
    summary { cursor: pointer; font-weight: 700; }
    .hint { color: #59697c; font-size: .9rem; }
    #conversation { list-style: none; padding: 0; }
    #conversation li { border-radius: .4rem; padding: .7rem; margin-bottom: .6rem;
                        background: #f0f4f9; overflow-wrap: anywhere; }
    #conversation li[data-role="user"] { background: #e5eefb; margin-left: 1rem; }
    #conversation li[data-role="application"] { background: #f4f5f6; font-size: .9rem; }
    #conversation p { white-space: pre-wrap; margin: .25rem 0 0; }
    #request-status, #filter-status { white-space: pre-wrap; }
    .error { color: #982e24; }
    @media (max-width: 42rem) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>Rental Assistant</h1>
  <p>Describe what you need, then review your filters or edit them directly.</p>
  <p class="hint">This version prepares filters. Listing search and saved listings come later.
    Conversation and filters reset when you reload the page.</p>
  <div class="layout">
    <aside aria-label="Search filters">
      <details id="filters-details">
        <summary>Editable filters</summary>
        <p class="hint">Click Apply filters to use direct edits. Applying also clears any unsent message.</p>
        <form id="filters-form" action="/filters/apply" method="post">
          <fieldset id="filter-fields">
            <label for="city">City</label><input id="city" name="city">
            <label for="state">State</label><input id="state" name="state">
            <label for="neighborhood">Neighborhood</label><input id="neighborhood" name="neighborhood">
            <label for="bedrooms">Bedrooms</label>
            <input id="bedrooms" name="bedrooms" type="number" step="1">
            <label for="max_monthly_rent">Maximum monthly rent ($)</label>
            <input id="max_monthly_rent" name="max_monthly_rent" type="number" step="any">
            <label for="dogs_allowed">Dogs allowed</label>
            <select id="dogs_allowed" name="dogs_allowed">
              <option value="">Unspecified</option>
              <option value="true">Yes</option><option value="false">No</option>
            </select>
            <label for="cats_allowed">Cats allowed</label>
            <select id="cats_allowed" name="cats_allowed">
              <option value="">Unspecified</option>
              <option value="true">Yes</option><option value="false">No</option>
            </select>
            <label for="amenities">Amenities (comma-separated)</label>
            <input id="amenities" name="amenities">
            <button id="apply-button" type="submit">Apply filters</button>
          </fieldset>
        </form>
      </details>
      <p id="filter-status" role="status">No filters applied yet.</p>
    </aside>
    <main>
      <section aria-labelledby="chat-heading">
        <h2 id="chat-heading">Chat</h2>
        <ol id="conversation" aria-label="Conversation" aria-live="polite"></ol>
        <form id="search-form" action="/search" method="post">
          <label for="message">Describe your rental needs</label>
          <textarea id="message" name="message" rows="3" required
            placeholder="Two bedrooms in Honolulu, HI, up to $2,500, with dogs allowed"></textarea>
          <p class="hint">Send uses your conversation and applied filters, and ignores unapplied edits.</p>
          <button id="submit" type="submit">Send</button>
        </form>
        <p id="request-status" role="status" aria-live="polite"></p>
      </section>
      <section aria-labelledby="results-heading">
        <h2 id="results-heading">Results</h2>
        <p id="results">Listing search is not connected yet. No properties have been searched.</p>
      </section>
      <section aria-labelledby="liked-heading">
        <h2 id="liked-heading">Liked</h2>
        <p>Liking and saved listings are not available yet.</p>
      </section>
    </main>
  </div>
  <script>
    const field = (id) => document.getElementById(id);
    const textFields = ['city', 'state', 'neighborhood'];
    const numberFields = ['bedrooms', 'max_monthly_rent'];
    const petFields = ['dogs_allowed', 'cats_allowed'];
    const state = {
      appliedFilters: {
        city: null, state: null, neighborhood: null, bedrooms: null,
        max_monthly_rent: null, dogs_allowed: null, cats_allowed: null, amenities: [],
      },
      draftFilters: null,
      clarificationQuestion: null,
      history: [],
      busy: false,
    };

    function setBusy(busy) {
      state.busy = busy;
      for (const id of ['submit', 'apply-button', 'message', 'filter-fields']) {
        field(id).disabled = busy;
      }
    }

    function requestStatus(text, error = false) {
      field('request-status').textContent = text;
      field('request-status').className = error ? 'error' : '';
    }

    function readFilters() {
      const filters = {};
      for (const key of textFields) filters[key] = field(key).value.trim() || null;
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

    function showFilters(filters) {
      for (const key of [...textFields, ...numberFields, ...petFields]) {
        field(key).value = filters[key] === null ? '' : String(filters[key]);
      }
      field('amenities').value = filters.amenities.join(', ');
      field('filters-details').open = true;
    }

    function acceptCandidate(data) {
      const candidate = structuredClone(data.filters);
      state.clarificationQuestion = data.clarification_question;
      if (state.clarificationQuestion) {
        state.draftFilters = candidate;
        field('filter-status').textContent = 'Draft needs clarification: ' + state.clarificationQuestion;
      } else {
        state.appliedFilters = candidate;
        state.draftFilters = null;
        field('filter-status').textContent = 'Filters applied. Listing search comes later.';
      }
      showFilters(candidate);
    }

    function recordEntry(role, content, filters = null) {
      const entry = {role, content};
      if (filters !== null) entry.filters = structuredClone(filters);
      state.history.push(entry);
      const item = document.createElement('li');
      item.dataset.role = role;
      const label = document.createElement('strong');
      label.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'Assistant' : 'Filters';
      const text = document.createElement('p');
      text.textContent = content;
      item.append(label, text);
      field('conversation').append(item);
    }

    function recordSnapshot(filters) {
      recordEntry('application', state.clarificationQuestion
        ? 'Pending filter draft: ' + state.clarificationQuestion
        : 'Filters applied.', filters);
    }

    async function post(path, payload) {
      const response = await fetch(path, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        let message = 'The request failed. Your changes are preserved; please try again.';
        try {
          const data = await response.json();
          if (typeof data.detail === 'string') message = data.detail;
          else if (response.status === 422) message = 'Check the entered values and try again.';
        } catch { /* Use the safe fallback for non-JSON errors. */ }
        throw new Error(message);
      }
      return response.json();
    }

    field('search-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      if (state.busy) return;
      const message = field('message').value.trim();
      if (!message) { requestStatus('Please enter a rental request.', true); return; }
      setBusy(true);
      requestStatus('Understanding your request...');
      try {
        const data = await post('/search', {
          message, filters: state.appliedFilters,
          draft_filters: state.draftFilters,
          clarification_question: state.clarificationQuestion,
          history: state.history,
        });
        acceptCandidate(data);
        recordEntry('user', message);
        const reply = [data.message, data.clarification_question]
          .filter((text, index, all) => text && all.indexOf(text) === index).join('\n');
        recordEntry('assistant', reply);
        recordSnapshot(data.filters);
        field('message').value = '';
        requestStatus('');
      } catch (error) {
        requestStatus(error.message || 'Unable to send. Your changes are preserved.', true);
      } finally {
        setBusy(false);
      }
    });

    field('filters-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      if (state.busy) return;
      const filters = readFilters();
      setBusy(true);
      requestStatus('Applying your filters...');
      try {
        const data = await post('/filters/apply', {filters});
        acceptCandidate(data);
        recordSnapshot(data.filters);
        field('message').value = '';
        requestStatus('');
      } catch (error) {
        requestStatus(error.message || 'Unable to apply. Your changes are preserved.', true);
      } finally {
        setBusy(false);
      }
    });

    field('filter-fields').addEventListener('input', () => {
      field('filter-status').textContent = 'Unapplied edits. Click Apply filters to use them.';
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
