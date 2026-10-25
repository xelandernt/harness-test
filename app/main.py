"""Application entry point.

The test suite imports ``create_app`` from this module and nothing else from
``app``.  Everything below ``/health`` is intentionally unimplemented.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build a fresh application instance with its own empty state."""
    application = FastAPI(title="EurExpense API", version="0.1.0")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application
