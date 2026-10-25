"""Health endpoint and routing sanity checks."""


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_path_returns_404(client):
    assert client.get("/not-a-route").status_code == 404
