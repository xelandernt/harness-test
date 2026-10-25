"""Authentication: token issuance and bearer-token enforcement."""

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin1234"


def test_login_returns_bearer_token(api):
    response = api.login(ADMIN_EMAIL, ADMIN_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) >= 16


def test_token_authorizes_admin_endpoint(api, client):
    token = api.token()

    response = client.get("/users", headers=api.headers(token))

    assert response.status_code == 200


def test_wrong_password_is_401(api):
    response = api.login(ADMIN_EMAIL, "not-the-password")

    assert response.status_code == 401
    assert isinstance(response.json().get("detail"), str)


def test_unknown_email_is_401(api):
    assert api.login("nobody@example.com", ADMIN_PASSWORD).status_code == 401


def test_missing_password_is_422(api, client):
    response = client.post("/auth/token", json={"email": ADMIN_EMAIL})

    assert response.status_code == 422


def test_email_matching_is_case_insensitive(api):
    assert api.login("ADMIN@EXAMPLE.COM", ADMIN_PASSWORD).status_code == 200


def test_missing_token_is_401(client):
    assert client.get("/expenses").status_code == 401


def test_malformed_authorization_header_is_401(client):
    response = client.get("/expenses", headers={"Authorization": "Token abc"})

    assert response.status_code == 401


def test_unknown_token_is_401(client):
    response = client.get("/expenses", headers={"Authorization": "Bearer definitely-not-valid"})

    assert response.status_code == 401


def test_each_login_issues_a_distinct_token(api):
    first = api.login(ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"]
    second = api.login(ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"]

    assert first != second
