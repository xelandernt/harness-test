"""User administration and reporting-line rules."""

ADMIN_EMAIL = "admin@example.com"
PASSWORD = "correct-horse-1"


def payload(**overrides):
    body = {
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "password": PASSWORD,
        "role": "employee",
    }
    body.update(overrides)
    return body


def create(api, token, **overrides):
    return api.client.post("/users", json=payload(**overrides), headers=api.headers(token))


def test_admin_creates_employee(api):
    admin = api.token()
    manager = api.create_user(admin, "manager@example.com", role="manager")

    response = create(api, admin, manager_id=manager["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["role"] == "employee"
    assert body["manager_id"] == manager["id"]
    assert body["id"]
    assert "password" not in body


def test_created_user_can_authenticate(api):
    admin = api.token()
    manager = api.create_user(admin, "manager@example.com", role="manager")
    create(api, admin, manager_id=manager["id"], email="newcomer@example.com")

    assert api.login("newcomer@example.com", PASSWORD).status_code == 200


def test_email_is_stored_lowercase(api):
    admin = api.token()

    response = create(api, admin, email="Ada@Example.COM", manager_id=api.admin_id(admin))

    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"
    assert api.login("ADA@EXAMPLE.COM", PASSWORD).status_code == 200


def test_duplicate_email_is_409(api):
    admin = api.token()
    manager = api.create_user(admin, "manager@example.com", role="manager")
    create(api, admin, manager_id=manager["id"])

    response = create(api, admin, email="ADA@EXAMPLE.COM", manager_id=manager["id"])

    assert response.status_code == 409


def test_employee_requires_a_manager(api):
    admin = api.token()

    assert create(api, admin).status_code == 422


def test_employee_manager_must_exist(api):
    admin = api.token()

    assert create(api, admin, manager_id="does-not-exist").status_code == 422


def test_employee_manager_must_be_a_manager_or_admin(api):
    admin = api.token()
    manager = api.create_user(admin, "manager@example.com", role="manager")
    colleague = api.create_user(admin, "colleague@example.com", manager_id=manager["id"])

    response = create(api, admin, manager_id=colleague["id"])

    assert response.status_code == 422


def test_manager_manager_must_be_an_admin(api):
    admin = api.token()
    manager = api.create_user(admin, "manager@example.com", role="manager")
    employee = api.create_user(admin, "employee@example.com", manager_id=manager["id"])

    response = create(api, admin, role="manager", manager_id=employee["id"])

    assert response.status_code == 422


def test_manager_may_report_to_an_admin(api):
    admin = api.token()

    response = create(api, admin, role="manager", manager_id=api.admin_id(admin))

    assert response.status_code == 201
    assert response.json()["manager_id"] == api.admin_id(admin)


def test_admin_cannot_have_a_manager(api):
    admin = api.token()

    response = create(api, admin, role="admin", manager_id=api.admin_id(admin))

    assert response.status_code == 422


def test_invalid_role_is_422(api):
    admin = api.token()

    assert create(api, admin, role="owner", manager_id=api.admin_id(admin)).status_code == 422


def test_short_password_is_422(api):
    admin = api.token()

    assert create(api, admin, password="short", manager_id=api.admin_id(admin)).status_code == 422


def test_invalid_email_is_422(api):
    admin = api.token()

    assert (
        create(api, admin, email="not-an-email", manager_id=api.admin_id(admin)).status_code == 422
    )


def test_blank_full_name_is_422(api):
    admin = api.token()

    assert create(api, admin, full_name="   ", manager_id=api.admin_id(admin)).status_code == 422


def test_unknown_field_is_422(api):
    admin = api.token()

    assert create(api, admin, nickname="ada", manager_id=api.admin_id(admin)).status_code == 422


def test_non_admin_cannot_create_users(api, world):
    response = create(
        api, world.employee_token, manager_id=world.manager["id"], email="another@example.com"
    )

    assert response.status_code == 403


def test_unauthenticated_create_is_401(api):
    assert api.client.post("/users", json=payload()).status_code == 401


def test_list_users_is_sorted_by_email(api):
    admin = api.token()
    manager = api.create_user(admin, "zoe@example.com", role="manager")
    api.create_user(admin, "adam@example.com", manager_id=manager["id"])

    response = api.client.get("/users", headers=api.headers(admin))

    assert response.status_code == 200
    users = response.json()
    emails = [user["email"] for user in users]
    assert emails == sorted(emails)
    assert ADMIN_EMAIL in emails
    assert "adam@example.com" in emails


def test_non_admin_cannot_list_users(api, world):
    response = api.client.get("/users", headers=api.headers(world.employee_token))

    assert response.status_code == 403


def test_user_can_read_themselves(api, world):
    response = api.client.get(
        f"/users/{world.employee['id']}", headers=api.headers(world.employee_token)
    )

    assert response.status_code == 200
    assert response.json()["email"] == "employee@example.com"


def test_admin_can_read_any_user(api, world):
    response = api.client.get(
        f"/users/{world.employee['id']}", headers=api.headers(world.admin_token)
    )

    assert response.status_code == 200


def test_colleague_cannot_read_another_user(api, world):
    response = api.client.get(
        f"/users/{world.other_employee['id']}",
        headers=api.headers(world.employee_token),
    )

    assert response.status_code == 403


def test_unknown_user_is_404(api, world):
    response = api.client.get("/users/no-such-user", headers=api.headers(world.admin_token))

    assert response.status_code == 404
