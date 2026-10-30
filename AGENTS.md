# Instructions for coding agents.
I want to build an apartment rental app that helps renters find relevant listings using natural English. Users will describe what they need, and the app will turn their words into search filters. They can check the filters and change them.

The full proposal is in docs/proposal.md.
## Layout
- app/main.py: routes and the page. No business rules.
- app/agent.py: the Pydantic AI agent and output model.
- app/rules.py: rules in plain Python. No FastAPI,
  no LLM client.
## Commands
```bash
uv run fastapi dev app/main.py   # run the app
uv run ruff check                # lint
uv run mypy                      # check types
uv run pytest                    # run the tests
```
## Spec
- `docs/proposal.md` is the spec. When a decision
  is made in a conversation (a feature added or
  left out, a limit or value chosen, an open
  question answered), edit the section the
  decision belongs to so that it states the
  decision, in the same change, and name that
  section in the pull request Summary. Change
  only what the decision affects. Do not add a
  dated log, approval history, or status notes;
  git and `docs/superpowers/` keep the history.
- A design under `docs/superpowers/specs/` covers
  one change; `docs/proposal.md` covers the whole
  project. If the two disagree, ask before
  building.
## Rules
- Tests never call a real model. Use TestModel with
  override_allow_model_requests(False).
- Read LLM_API_TOKEN and LLM_API_GATEWAY from the
  environment. Never write a key outside .env.
- Run ruff, mypy, and pytest after every change and
  include their output. Never report done while one
  fails.
- Never weaken a check: no raised max-complexity, 
no # noqa or # type: ignore, no skipped tests.
## Changes
- Never commit to main. Make each change on its own
  branch and open a pull request with gh pr create.
  The description has a ## Summary (what changed and
  why, citing docs/proposal.md) and a ## Test plan
  checklist (checked items were run; unchecked items
  are left for the reviewer).
- When preparing, creating, or updating a pull request,
  use `.agents/skills/pr-review-diagrams/SKILL.md`.
  Include its Diagram section before the Test plan
  to explain the changed flow or structure.
- After pushing, run gh pr checks --watch and report
  the result.
-  Never merge a pull request. The person merges
  after reviewing it.
