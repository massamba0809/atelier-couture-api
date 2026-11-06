"""Route 44 : GET /health (publique, hors préfixe /api/v1)."""


def test_health_sans_jeton_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
