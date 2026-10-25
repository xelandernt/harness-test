# EurExpense API — common tasks

set shell := ["bash", "-uc"]

[default, private]
_:
    @just --list

# Install and sync dependencies
install:
    uv sync

# Upgrade dependencies within the declared constraints
upgrade:
    uv lock --upgrade
    uv sync

# Format the codebase
format:
    uv run ruff format .

# Format and lint, applying safe fixes
lint:
    uv run ruff format .
    uv run ruff check --fix .

# Run every check: formatting, lint, types, and tests
check: check-format check-lint check-types test

# Verify formatting without changing files
check-format:
    uv run ruff format --check .

# Verify lint without changing files
check-lint:
    uv run ruff check .

# Type check with pyrefly
check-types:
    uv run pyrefly check

# Run the test suite
test:
    uv run pytest

# List the test suite without running it
collect:
    uv run pytest --collect-only -q

# Remove the virtual environment and tool caches
clean:
    rm -rf .venv .pytest_cache .ruff_cache .pyrefly_cache app/__pycache__ tests/__pycache__
