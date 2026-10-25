# Task

Implement the **EurExpense Approval API** described in [`SPEC.md`](./SPEC.md).

The repository gives you:

- `SPEC.md` — the authoritative contract: domain rules, endpoints, status codes,
  and edge cases.
- `tests/` — the executable version of that contract, built with `pytest` and
  FastAPI's `TestClient`.
- `app/` — a skeleton with a single working route (`GET /health`).

Everything below `/health` is yours to design and build.

## Setup and verification

```bash
uv sync
uv run pytest
```

`uv run pytest` is the only command used to judge the result. The suite is
expected to fail when you start.

## Rules

- **`tests/` is read-only.** Do not modify, delete, rename, or add files under
  `tests/`, including `conftest.py`. Do not add `skip` or `xfail` markers,
  weaken assertions, or change pytest configuration. A run that alters the
  suite is invalid regardless of how many tests pass.
- **Only `app/` may be modified.** Implementation code belongs there.
- **Do not add dependencies.** `fastapi`, `pydantic`, `email-validator`, and
  their transitive dependencies are already available; the grading environment
  is offline.
- **Do not special-case the tests.** No detecting the test client, no branching
  on environment variables, no hard-coded responses keyed to specific inputs.
- The suite imports exactly one symbol from your code:
  `from app.main import create_app`. Each `create_app()` call must return an
  app with fresh, isolated in-memory state.

## Quality gates

The repository ships `ruff` (lint + format) and `pyrefly` (type checking) and is
clean under all three:

```bash
uv run ruff check
uv run ruff format --check
uv run pyrefly check
```

Keep them clean. A submission that leaves any of these failing is not finished.

## Done when

`uv run pytest` passes with no changes to `tests/`, `pyproject.toml`, or
`SPEC.md`, and the quality gates above pass.
