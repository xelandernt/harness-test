# EurExpense API

EurExpense is an expense-approval API built with FastAPI and Pydantic. Employees
record expenses, managers approve or reject them, and admins manage users and
reporting lines.

The repository contains:

- `SPEC.md` — the authoritative behaviour contract
- `tests/` — the executable form of that contract
- `app/` — a runnable application skeleton

## Status

Only `GET /health` is implemented. The rest of the API is unimplemented, so most
of the suite fails. That is the expected starting point.

## Quickstart

```bash
uv sync
uv run pytest
```

## Layout

```
SPEC.md          behaviour contract: routes, rules, status codes, edge cases
app/main.py      create_app() + GET /health
tests/           130 black-box tests, grouped by feature area
pyproject.toml   dependencies, tooling, and pytest configuration
uv.lock          pinned dependency graph
```

## Contract

- The test suite imports exactly one symbol: `app.main.create_app`.
- Each `create_app()` call returns an app with fresh, isolated in-memory state.
- Storage is in memory: no database, no files, no network.
- `tests/` is read-only. Do not edit, skip, or weaken tests.
- Implementation code lives in `app/`. Dependencies are fixed and the
  environment has no network access.

## Quality gates

The repository is lint- and type-check clean and should stay that way:

```bash
uv run ruff check
uv run ruff format --check
uv run pyrefly check
```

## Development

Common tasks are wrapped in the `justfile` (requires [just](https://github.com/casey/just)):

```bash
just install      # sync dependencies
just check        # format check, lint, types, and tests
just test         # run the test suite
just format       # format the codebase
just lint         # format and lint with fixes
just upgrade      # refresh the lockfile
```

The underlying commands work without `just`:

```bash
uv sync
uv run pytest --collect-only -q   # list the suite
uv run ruff format .              # format
uv run ruff check --fix .         # lint
uv run pyrefly check              # type check
```

## License

See [LICENSE](./LICENSE).
