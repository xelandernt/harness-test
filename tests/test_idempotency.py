"""Idempotency-Key semantics for expense creation."""

KEY = "expense-key-1234"


def test_replay_returns_the_original_expense(api, world):
    first = api.create_expense(world.employee_token, idempotency_key=KEY)
    replay = api.create_expense(world.employee_token, idempotency_key=KEY)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["amount"] == "12.50"


def test_replay_does_not_create_a_second_expense(api, world):
    api.create_expense(world.employee_token, idempotency_key=KEY)
    api.create_expense(world.employee_token, idempotency_key=KEY)

    response = api.list_expenses(world.employee_token)

    assert response.json()["total"] == 1


def test_replay_returns_the_current_state(api, world):
    first = api.create_expense(world.employee_token, idempotency_key=KEY).json()
    assert api.submit(world.employee_token, first["id"]).status_code == 200

    replay = api.create_expense(world.employee_token, idempotency_key=KEY)

    assert replay.status_code == 200
    assert replay.json()["status"] == "submitted"


def test_reusing_a_key_with_a_different_payload_is_409(api, world):
    api.create_expense(world.employee_token, idempotency_key=KEY)

    response = api.create_expense(world.employee_token, amount="13.00", idempotency_key=KEY)

    assert response.status_code == 409


def test_keys_are_scoped_per_owner(api, world):
    first = api.create_expense(world.employee_token, idempotency_key=KEY)
    second = api.create_expense(world.other_employee_token, idempotency_key=KEY)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_short_key_is_422(api, world):
    response = api.create_expense(world.employee_token, idempotency_key="short")

    assert response.status_code == 422


def test_long_key_is_422(api, world):
    response = api.create_expense(world.employee_token, idempotency_key="k" * 65)

    assert response.status_code == 422


def test_maximum_length_key_is_accepted(api, world):
    key = "k" * 64

    first = api.create_expense(world.employee_token, idempotency_key=key)
    replay = api.create_expense(world.employee_token, idempotency_key=key)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]


def test_without_a_key_requests_are_independent(api, world):
    first = api.create_expense(world.employee_token)
    second = api.create_expense(world.employee_token)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_normalized_payload_counts_as_the_same_request(api, world):
    first = api.create_expense(world.employee_token, category="TRAVEL", idempotency_key=KEY)
    replay = api.create_expense(world.employee_token, category="travel", idempotency_key=KEY)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
