# Rental Assistant

A FastAPI page that turns rental requests into editable search filters using a
Pydantic AI agent. Chat includes the current tab's conversation history, applied
filters, and any draft awaiting clarification.

## Run locally

Install the locked dependencies:

```sh
uv sync --locked --dev
```

If you do not already have a `.env`, copy `.env.example` to `.env` and fill in your
course gateway token there. Keep an existing `.env` and its token intact.

- `LLM_API_GATEWAY`: `https://128.171.10.83:9443/v1`
- `LLM_API_TOKEN`: your course token, kept on the server only
- `LLM_MODEL`: optional; defaults to `gpt-oss-120b`

Existing process environment variables take precedence over `.env`. The gateway
uses OpenAI-compatible Chat Completions for this model. Read the
[gateway documentation](https://128.171.10.83:9443/llms.txt) for model availability
and account access. The app does not use the Responses API or retry failed
authentication/budget requests.

```sh
uv run fastapi dev app/main.py
```

Open the local URL printed by FastAPI. The page and manual filter Apply work
without model credentials; chat requires the configured gateway.

## Apply and Send

- **Apply filters** submits exactly the visible edits without a model call and
  clears the unsent chat message after a successful submission.
- **Send** ignores unapplied manual edits, supplies the current state and full
  conversation history to the model, and automatically applies relevant changes.
  Requirements not mentioned in the new message stay unchanged. The model can
  remove a requirement when explicitly asked.
- A missing city/state or an ambiguous requirement remains a clarification draft.
  Earlier complete filters are preserved until the draft is complete. Direct
  Apply can supersede a chat draft; a later message can finish an incomplete
  manually applied draft.
- Failed requests preserve the conversation, applied state, edits, and unsent
  message so you can retry. Both submission paths are disabled while waiting.

This version prepares filters only. Listing retrieval, RAG, SQLite persistence,
and working Liked listings are still future work. Conversation and filters live
only in the current tab and reset on reload; there are no accounts or login.

## Checks

```sh
uv run ruff check
uv run mypy
uv run pytest
```

Automated tests deny all real model requests and use Pydantic AI `TestModel` for
agent and endpoint coverage. They establish the application's state/context
contracts, not the live model's reasoning accuracy.

## Browser walkthrough

1. Open Editable filters. Set Honolulu, HI, 2 bedrooms, a $2,500 budget, and dogs
   allowed. Type an unsent chat message and click **Apply filters**. The message
   clears, the filters are applied, and no model request is needed.
2. Edit the budget to $2,300 and bedrooms to 9 without applying. Send "Lower my
   budget to $2,200." The returned filters should use $2,200 and keep 2 bedrooms.
3. Clear city and state, set Downtown and 3 bedrooms, and Apply. The app asks for
   city/state while preserving the prior complete state. Edit bedrooms to 9 but
   do not apply; send "Honolulu, HI." The completed draft should keep 3 bedrooms.
4. Send a request that references an earlier message, such as "Use the budget I
   originally mentioned." Review the extracted values; this exercises live model
   interpretation of the supplied history.
5. Send an unrelated question. Existing filters and any pending clarification
   should stay unchanged.
6. While a response is pending, verify Send, Apply, the message, and filter inputs
   are disabled. Use the browser's offline mode for a subsequent submission and
   confirm an error leaves the edits and message intact.

The implementation was also exercised in a real headless Chromium browser against
a local deterministic TestModel server for input priority, clarification, failure
preservation, busy controls, and rendering message content as literal text.
