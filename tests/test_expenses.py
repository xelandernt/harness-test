"""Expense creation, validation, reads, edits, and deletion."""

from datetime import datetime


def expense_payload(**overrides):
    body = {
        "amount": "12.50",
        "category": "travel",
        "description": "Client visit",
    }
    body.update(overrides)
    return body


def post(api, token, **overrides):
    return api.client.post(
        "/expenses", json=expense_payload(**overrides), headers=api.headers(token)
    )


def timestamp(value):
    assert isinstance(value, str)
    return datetime.fromisoformat(value)


def test_create_returns_a_draft(api, world):
    response = api.create_expense(world.employee_token)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["owner_id"] == world.employee["id"]
    assert body["amount"] == "12.50"
    assert body["currency"] == "EUR"
    assert body["category"] == "travel"
    assert body["description"] == "Client visit"
    assert body["status"] == "draft"
    assert body["submitted_at"] is None
    assert body["decided_at"] is None
    assert body["decided_by"] is None
    assert body["rejection_reason"] is None
    assert timestamp(body["created_at"]).tzinfo is not None


def test_single_decimal_amount_is_422(api, world):
    assert post(api, world.employee_token, amount="10.5").status_code == 422


def test_numeric_amount_is_422(api, world):
    assert post(api, world.employee_token, amount=10.5).status_code == 422


def test_zero_amount_is_422(api, world):
    assert post(api, world.employee_token, amount="0.00").status_code == 422


def test_negative_amount_is_422(api, world):
    assert post(api, world.employee_token, amount="-1.00").status_code == 422


def test_more_than_two_decimals_is_422(api, world):
    assert post(api, world.employee_token, amount="10.001").status_code == 422


def test_amount_above_maximum_is_422(api, world):
    assert post(api, world.employee_token, amount="100000.01").status_code == 422


def test_blank_description_is_422(api, world):
    assert post(api, world.employee_token, description="   ").status_code == 422


def test_over_long_description_is_422(api, world):
    assert post(api, world.employee_token, description="x" * 501).status_code == 422


def test_description_is_trimmed(api, world):
    response = post(api, world.employee_token, description="  Client visit  ")

    assert response.status_code == 201
    assert response.json()["description"] == "Client visit"


def test_category_is_case_insensitive(api, world):
    response = post(api, world.employee_token, category="TRAVEL")

    assert response.status_code == 201
    assert response.json()["category"] == "travel"


def test_unknown_category_is_422(api, world):
    assert post(api, world.employee_token, category="entertainment").status_code == 422


def test_currency_defaults_to_eur(api, world):
    response = api.create_expense(world.employee_token)

    assert response.status_code == 201
    assert response.json()["currency"] == "EUR"


def test_currency_is_case_insensitive(api, world):
    response = post(api, world.employee_token, currency="eur")

    assert response.status_code == 201
    assert response.json()["currency"] == "EUR"


def test_non_eur_currency_is_422(api, world):
    assert post(api, world.employee_token, currency="USD").status_code == 422


def test_unknown_field_is_422(api, world):
    assert post(api, world.employee_token, status="approved").status_code == 422


def test_manager_can_own_an_expense(api, world):
    response = api.create_expense(world.manager_token)

    assert response.status_code == 201
    assert response.json()["owner_id"] == world.manager["id"]


def test_admin_can_own_an_expense(api, world):
    response = api.create_expense(world.admin_token)

    assert response.status_code == 201
    assert response.json()["owner_id"] == world.admin_id


def test_unauthenticated_create_is_401(api):
    assert api.client.post("/expenses", json=expense_payload()).status_code == 401


def test_owner_can_read_their_expense(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.get_expense(world.employee_token, expense["id"])

    assert response.status_code == 200
    assert response.json()["id"] == expense["id"]


def test_direct_manager_can_read_expense(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.get_expense(world.manager_token, expense["id"])

    assert response.status_code == 200


def test_admin_can_read_any_expense(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.get_expense(world.admin_token, expense["id"])

    assert response.status_code == 200


def test_unrelated_employee_cannot_read_expense(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.get_expense(world.other_employee_token, expense["id"])

    assert response.status_code == 403


def test_unknown_expense_is_404(api, world):
    assert api.get_expense(world.employee_token, "no-such-expense").status_code == 404


def test_owner_can_edit_a_draft(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.patch(
        f"/expenses/{expense['id']}",
        json={"amount": "20.00", "category": "meals", "description": "Lunch"},
        headers=api.headers(world.employee_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "20.00"
    assert body["category"] == "meals"
    assert body["description"] == "Lunch"


def test_empty_patch_is_422(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.patch(
        f"/expenses/{expense['id']}",
        json={},
        headers=api.headers(world.employee_token),
    )

    assert response.status_code == 422


def test_status_cannot_be_patched(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.patch(
        f"/expenses/{expense['id']}",
        json={"status": "approved"},
        headers=api.headers(world.employee_token),
    )

    assert response.status_code == 422


def test_non_owner_cannot_edit(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.patch(
        f"/expenses/{expense['id']}",
        json={"amount": "20.00"},
        headers=api.headers(world.manager_token),
    )

    assert response.status_code == 403


def test_submitted_expense_cannot_be_edited(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.client.patch(
        f"/expenses/{expense['id']}",
        json={"amount": "20.00"},
        headers=api.headers(world.employee_token),
    )

    assert response.status_code == 409


def test_owner_can_delete_a_draft(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.delete(
        f"/expenses/{expense['id']}", headers=api.headers(world.employee_token)
    )

    assert response.status_code == 204
    assert response.content == b""
    assert api.get_expense(world.employee_token, expense["id"]).status_code == 404


def test_submitted_expense_cannot_be_deleted(api, world):
    expense = api.submitted_expense(world.employee_token)

    response = api.client.delete(
        f"/expenses/{expense['id']}", headers=api.headers(world.employee_token)
    )

    assert response.status_code == 409


def test_non_owner_cannot_delete(api, world):
    expense = api.make_expense(world.employee_token)

    response = api.client.delete(
        f"/expenses/{expense['id']}", headers=api.headers(world.manager_token)
    )

    assert response.status_code == 403
