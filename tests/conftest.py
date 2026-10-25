"""Shared fixtures and HTTP helpers.

Everything here talks to the application over HTTP.  No test imports anything
from ``app`` except ``app.main.create_app``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin1234"
DEFAULT_PASSWORD = "correct-horse-1"


@dataclass(frozen=True)
class World:
    """A small organisation: one admin, two managers, two employees."""

    admin_id: str
    admin_token: str
    manager: dict
    manager_token: str
    employee: dict
    employee_token: str
    other_manager: dict
    other_manager_token: str
    other_employee: dict
    other_employee_token: str


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


class Api:
    """Thin HTTP helper around a TestClient."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    @staticmethod
    def headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def login(self, email: str, password: str):
        return self.client.post("/auth/token", json={"email": email, "password": password})

    def token(self, email: str = ADMIN_EMAIL, password: str | None = None) -> str:
        if password is None:
            password = ADMIN_PASSWORD if email.lower() == ADMIN_EMAIL else DEFAULT_PASSWORD
        response = self.login(email, password)
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    def admin_id(self, token: str | None = None) -> str:
        token = token or self.token()
        response = self.client.get("/users", headers=self.headers(token))
        assert response.status_code == 200, response.text
        for user in response.json():
            if user["email"] == ADMIN_EMAIL:
                return user["id"]
        raise AssertionError("seeded admin is missing from GET /users")

    def create_user(
        self,
        token: str,
        email: str,
        *,
        role: str = "employee",
        manager_id: str | None = None,
        password: str = DEFAULT_PASSWORD,
        full_name: str | None = None,
    ) -> dict:
        response = self.client.post(
            "/users",
            json={
                "email": email,
                "full_name": full_name or email.split("@")[0].replace(".", " ").title(),
                "password": password,
                "role": role,
                "manager_id": manager_id,
            },
            headers=self.headers(token),
        )
        assert response.status_code == 201, response.text
        return response.json()

    # -- expenses ---------------------------------------------------------

    def create_expense(
        self,
        token: str,
        *,
        amount: str = "12.50",
        category: str = "travel",
        description: str = "Client visit",
        currency: str | None = None,
        idempotency_key: str | None = None,
    ):
        payload = {
            "amount": amount,
            "category": category,
            "description": description,
        }
        if currency is not None:
            payload["currency"] = currency
        headers = self.headers(token)
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return self.client.post("/expenses", json=payload, headers=headers)

    def make_expense(self, token: str, **kwargs) -> dict:
        response = self.create_expense(token, **kwargs)
        assert response.status_code == 201, response.text
        return response.json()

    def submitted_expense(self, token: str, **kwargs) -> dict:
        expense = self.make_expense(token, **kwargs)
        response = self.submit(token, expense["id"])
        assert response.status_code == 200, response.text
        return response.json()

    def get_expense(self, token: str, expense_id: str):
        return self.client.get(f"/expenses/{expense_id}", headers=self.headers(token))

    def submit(self, token: str, expense_id: str):
        return self.client.post(f"/expenses/{expense_id}/submit", headers=self.headers(token))

    def approve(self, token: str, expense_id: str):
        return self.client.post(f"/expenses/{expense_id}/approve", headers=self.headers(token))

    def reject(self, token: str, expense_id: str, reason: str):
        return self.client.post(
            f"/expenses/{expense_id}/reject",
            json={"reason": reason},
            headers=self.headers(token),
        )

    def list_expenses(self, token: str, **params):
        return self.client.get("/expenses", params=params, headers=self.headers(token))


@pytest.fixture()
def api(client: TestClient) -> Api:
    return Api(client)


@pytest.fixture()
def world(api: Api) -> World:
    admin_token = api.token()
    admin_id = api.admin_id(admin_token)
    manager = api.create_user(admin_token, "manager@example.com", role="manager")
    employee = api.create_user(admin_token, "employee@example.com", manager_id=manager["id"])
    other_manager = api.create_user(admin_token, "other.manager@example.com", role="manager")
    other_employee = api.create_user(
        admin_token, "other.employee@example.com", manager_id=other_manager["id"]
    )
    return World(
        admin_id=admin_id,
        admin_token=admin_token,
        manager=manager,
        manager_token=api.token("manager@example.com"),
        employee=employee,
        employee_token=api.token("employee@example.com"),
        other_manager=other_manager,
        other_manager_token=api.token("other.manager@example.com"),
        other_employee=other_employee,
        other_employee_token=api.token("other.employee@example.com"),
    )
