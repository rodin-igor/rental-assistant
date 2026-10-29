# Conversational Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder response with history-aware model extraction and direct Apply, preserving the approved input priorities and clarification drafts.

**Architecture:** The browser owns applied filters, a clarification draft, and the visible manual edits. A Pydantic AI agent returns field changes; a service merges only those changes using plain Python rules. Thin FastAPI routes return the existing four response fields for both chat and manual Apply.

**Tech Stack:** Existing FastAPI, Pydantic AI, Python, vanilla HTML/JavaScript; OpenAI-compatible Chat Completions through the course gateway.

**Spec:** `docs/superpowers/specs/2026-10-29-conversational-filters-design.md`

## Global Constraints

- Use `gpt-oss-120b`, with a configurable `LLM_MODEL` default and server-only `LLM_API_GATEWAY` / `LLM_API_TOKEN`.
- Gateway base URL is `https://128.171.10.83:9443/v1`; use Chat Completions, not Responses.
- Automated tests use `TestModel` and `override_allow_model_requests(False)`; no live model calls.
- No retrieval, database implementation, accounts, working Likes, streaming, or silent history truncation.
- Keep routes/page in `app/main.py`, agent/output in `app/agent.py`, and plain Python rules in `app/rules.py`.
- Run `uv run ruff check`, `uv run mypy`, and `uv run pytest` after each coherent edit, including the expected red test stage. Never weaken checks.

## Review Focus

- Explicit null clears a requirement, while an omitted change preserves it: agent/service tests.
- An incomplete manual Apply supersedes an older chat draft and survives a later clarification: endpoint and browser checks.
- Unrelated messages cannot apply model-suggested accidental changes or clear a pending clarification: service tests.
- Failed chat must preserve manual edits, the unsent message, and applied state: endpoint error and browser checks.
- Concurrent clicks cannot let an old chat response overwrite an Apply: browser check with a delayed response.

## Files and responsibilities

- `app/agent.py`: typed context/history/change models, lazy gateway configuration, agent instructions, history translation.
- `app/rules.py`: merge supplied changes and generate missing-location questions without LLM/FastAPI imports.
- `app/service.py`: coordinate interpretation, relevance, merging, clarification, and safe upstream errors.
- `app/main.py`: GET page, POST `/search`, POST `/filters/apply`, safe error rendering, browser state/transcript.
- `tests/conftest.py`: deny real model requests and inject deterministic TestModel at the gateway dependency.
- `tests/test_agent.py`, `tests/test_search.py`, `tests/test_rules.py`: behavior and context tests; preserve skeleton checks.
- `.env.example`, `README.md`, `.gitignore`: configuration placeholders, manual browser walkthrough, ignore local previews.

### Task 1: Agent and field-change contracts

**Interfaces:**
- `FilterChanges` has optional existing filter fields; `model_dump(exclude_unset=True)` distinguishes omitted fields from explicit null.
- `FilterInterpretation(message, changes, relevant, clarification_question)` is the agent output.
- `ConversationEntry(role, content, filters)` accepts user/assistant/application roles only; optional filter snapshots are conversation data.
- `SearchRequest` retains `message` and `filters`, adding `history`, `draft_filters`, and `clarification_question`.
- `rental_agent` is `Agent[None, FilterInterpretation]`; `interpret(request: SearchRequest, model: Model) -> FilterInterpretation` passes typed history and explicitly labeled current state.
- `get_model() -> Model` creates an OpenAIChatModel lazily; `AgentUnavailableError` exposes safe configuration errors.

- [ ] Write `tests/test_agent.py`: inspect real captured agent messages under TestModel for past user/assistant text, applied snapshots, current state and draft. Verify null versus omission, rejected system roles and blank messages, configuration base URL/model and disabled SDK retries.
- [ ] Run `uv run pytest tests/test_agent.py -q` and observe the missing-contract failure; also run Ruff and mypy.
- [ ] Implement the models, lazy gateway client with SDK retries disabled, non-strict output-tool schema, instructions, and history translation. No provider is constructed at import time.
- [ ] Run the full checks and confirm green, retaining the placeholder route for this task.
- [ ] Commit the agent contract and tests.

### Task 2: Service, rules, and endpoint behavior

**Interfaces:**
- `merge_filter_changes(current: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]` preserves absent keys; null amenities becomes an empty list.
- `location_question(city: str | None, state: str | None) -> str | None` uses `has_complete_location`.
- `interpret_search(request: SearchRequest, model: Model) -> SearchResponse` is async; `apply_filters(request: ApplyRequest) -> SearchResponse` never uses an agent.
- `ApplyRequest.filters` is the complete directly edited snapshot.
- Responses retain exactly `message`, `filters`, `listings`, `clarification_question`. Listings are empty. A non-null question marks the returned filters as a draft.
- FastAPI uses `Depends(get_model)` for `/search` only and maps `AgentUnavailableError` to a safe 503 response.

- [ ] Write rule/service/endpoint tests for partial budget updates, explicit removal, draft clarification, unrelated changes, complete/incomplete Apply with zero model access, history inclusion, blank request validation and safe model failure.
- [ ] Preserve both skeleton checks; inject TestModel instead of allowing the new live endpoint to initialize a gateway client.
- [ ] Run the full checks; observe the expected endpoint/rule failures.
- [ ] Implement plain merge/location rules, orchestration, both typed endpoints and safe configuration/upstream errors. Preserve optional budget and existing filter fields.
- [ ] Run all checks, confirm green, and commit.

### Task 3: Browser workflow and documentation

**Interfaces:**
- Browser state contains `appliedFilters`, `draftFilters`, `clarificationQuestion`, `history`, and `busy`.
- Send posts state/history and new text, never reading edited filter controls. Success accepts the candidate, appends user/assistant/context history, and clears the message. Failure leaves all drafts intact.
- Apply posts edited controls to `/filters/apply`; success clears unsent text, supersedes older clarification, and records the resulting snapshot without a model call.
- Both actions keep incomplete candidates as `draftFilters`; complete candidates replace `appliedFilters`.
- A disabled form/fieldset plus a busy guard prevents conflicting input while a request is in flight. All model/user text is rendered with `textContent`.

- [ ] Write a failing browser behavior check using installed headless Chromium and a local TestModel app: verify Apply/Send priority, clearing unsent text, draft completion, failure preservation and busy controls. Keep temporary browser artifacts in ignored local scratch, not a new browser dependency in pytest.
- [ ] Replace the placeholder UI behavior with the state/transcript above. Keep `search-form`, initially hidden filters, and Results/Liked placeholders.
- [ ] Document setup and a reproducible manual walkthrough in README; add `LLM_MODEL` and the non-secret gateway URL to `.env.example`; ignore `.superpowers/`.
- [ ] Run the browser walkthrough and Ruff/mypy/pytest. Record what the browser check establishes separately from real model quality; do not call the live gateway in tests.
- [ ] Commit the page and documentation, then request one independent whole-branch review. Fix important findings with failing regression checks first.
- [ ] Push, create the implementation PR with Summary and Test plan, watch checks, and leave merging to the user.

## Execution notes

The user explicitly approved the design and requested building it. Execute in this session without another approval pause. Work on `feat/conversational-filters` in the existing checkout; preserve the user's uncommitted `AGENTS.md` edit. The approved design PR is still open, so this implementation branch includes its documentation commit and the final PR will describe the full finished change.
