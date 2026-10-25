"""Category policy limits, enforced at submit time."""

from datetime import datetime

import pytest

LIMITS = [
    ("travel", "1000.00"),
    ("meals", "75.00"),
    ("equipment", "2500.00"),
    ("training", "800.00"),
    ("other", "500.00"),
]


def timestamp(value):
    return datetime.fromisoformat(value)


@pytest.mark.parametrize(("category", "limit"), LIMITS)
def test_amount_at_the_limit_can_be_submitted(api, world, category, limit):
    expense = api.make_expense(world.employee_token, amount=limit, category=category)

    response = api.submit(world.employee_token, expense["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"


def test_one_cent_over_the_limit_cannot_be_submitted(api, world):
    expense = api.make_expense(world.employee_token, amount="75.01", category="meals")

    response = api.submit(world.employee_token, expense["id"])

    assert response.status_code == 422
    stored = api.get_expense(world.employee_token, expense["id"]).json()
    assert stored["status"] == "draft"
    assert stored["submitted_at"] is None


def test_draft_may_exceed_the_limit(api, world):
    response = api.create_expense(world.employee_token, amount="1000.01", category="travel")

    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_reducing_the_amount_allows_submission(api, world):
    expense = api.make_expense(world.employee_token, amount="75.01", category="meals")

    patched = api.client.patch(
        f"/expenses/{expense['id']}",
        json={"amount": "75.00"},
        headers=api.headers(world.employee_token),
    )
    assert patched.status_code == 200

    assert api.submit(world.employee_token, expense["id"]).status_code == 200


def test_submission_records_a_timestamp(api, world):
    response = api.submit(world.employee_token, api.make_expense(world.employee_token)["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None
    assert timestamp(body["submitted_at"]).tzinfo is not None
    assert timestamp(body["submitted_at"]) >= timestamp(body["created_at"])
    assert body["decided_at"] is None
    assert body["decided_by"] is None


def test_non_owner_cannot_submit(api, world):
    expense = api.make_expense(world.employee_token)

    assert api.submit(world.manager_token, expense["id"]).status_code == 403


def test_submitting_twice_is_409(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.submit(world.employee_token, expense["id"]).status_code == 409


def test_approved_expense_cannot_be_submitted(api, world):
    expense = api.submitted_expense(world.employee_token)
    assert api.approve(world.manager_token, expense["id"]).status_code == 200

    assert api.submit(world.employee_token, expense["id"]).status_code == 409


def test_rejected_expense_cannot_be_submitted(api, world):
    expense = api.submitted_expense(world.employee_token)
    assert api.reject(world.manager_token, expense["id"], "No receipt").status_code == 200

    assert api.submit(world.employee_token, expense["id"]).status_code == 409


def test_unknown_expense_cannot_be_submitted(api, world):
    assert api.submit(world.employee_token, "no-such-expense").status_code == 404


def test_unauthenticated_submit_is_401(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.post(f"/expenses/{expense['id']}/submit")

    assert response.status_code == 401
