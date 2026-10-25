"""Approval and rejection: authorization, transitions, and decision fields."""

from datetime import datetime


def timestamp(value):
    return datetime.fromisoformat(value)


def test_direct_manager_approves(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.approve(world.manager_token, expense["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["decided_by"] == world.manager["id"]
    assert body["decided_at"] is not None
    assert timestamp(body["decided_at"]).tzinfo is not None
    assert body["rejection_reason"] is None


def test_admin_approves_employee_expense(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.approve(world.admin_token, expense["id"])

    assert response.status_code == 200
    assert response.json()["decided_by"] == world.admin_id


def test_owner_cannot_approve_their_own_expense(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.approve(world.employee_token, expense["id"]).status_code == 403


def test_admin_cannot_approve_their_own_expense(api, world):
    expense = api.submitted_expense(world.admin_token)

    assert api.approve(world.admin_token, expense["id"]).status_code == 403


def test_unrelated_employee_cannot_approve(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.approve(world.other_employee_token, expense["id"]).status_code == 403


def test_other_manager_cannot_approve(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.approve(world.other_manager_token, expense["id"]).status_code == 403


def test_report_cannot_approve_their_manager(api, world):
    expense = api.submitted_expense(world.manager_token)

    assert api.approve(world.employee_token, expense["id"]).status_code == 403


def test_draft_cannot_be_approved(api, world):
    expense = api.make_expense(world.employee_token)

    assert api.approve(world.manager_token, expense["id"]).status_code == 409


def test_expense_cannot_be_approved_twice(api, world):
    expense = api.submitted_expense(world.employee_token)
    assert api.approve(world.manager_token, expense["id"]).status_code == 200

    assert api.approve(world.manager_token, expense["id"]).status_code == 409


def test_rejected_expense_cannot_be_approved(api, world):
    expense = api.submitted_expense(world.employee_token)
    assert api.reject(world.manager_token, expense["id"], "No receipt").status_code == 200

    assert api.approve(world.manager_token, expense["id"]).status_code == 409


def test_unknown_expense_cannot_be_approved(api, world):
    assert api.approve(world.manager_token, "no-such-expense").status_code == 404


def test_unauthenticated_approval_is_401(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.client.post(f"/expenses/{expense['id']}/approve")

    assert response.status_code == 401


def test_manager_rejects_with_trimmed_reason(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.reject(world.manager_token, expense["id"], "  Missing receipt  ")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Missing receipt"
    assert body["decided_by"] == world.manager["id"]
    assert body["decided_at"] is not None


def test_rejection_requires_a_reason(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.client.post(
        f"/expenses/{expense['id']}/reject",
        json={},
        headers=api.headers(world.manager_token),
    )

    assert response.status_code == 422


def test_blank_rejection_reason_is_422(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.reject(world.manager_token, expense["id"], "   ").status_code == 422


def test_over_long_rejection_reason_is_422(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.reject(world.manager_token, expense["id"], "x" * 501).status_code == 422


def test_other_manager_cannot_reject(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.reject(world.other_manager_token, expense["id"], "No").status_code == 403


def test_owner_cannot_reject_their_own_expense(api, world):
    expense = api.submitted_expense(world.employee_token)

    assert api.reject(world.employee_token, expense["id"], "No").status_code == 403


def test_expense_cannot_be_rejected_twice(api, world):
    expense = api.submitted_expense(world.employee_token)
    assert api.reject(world.manager_token, expense["id"], "No receipt").status_code == 200

    assert api.reject(world.manager_token, expense["id"], "Again").status_code == 409


def test_another_admin_can_decide_an_admins_expense(api, world):
    second_admin = api.create_user(world.admin_token, "admin.two@example.com", role="admin")
    second_admin_token = api.token("admin.two@example.com")
    expense = api.submitted_expense(world.admin_token)

    response = api.approve(second_admin_token, expense["id"])

    assert response.status_code == 200
    assert response.json()["decided_by"] == second_admin["id"]
