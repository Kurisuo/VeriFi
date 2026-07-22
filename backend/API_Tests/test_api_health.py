"""API bridge tests: GET /health."""

import main


def test_api_health_ok_when_chunks_present(client, monkeypatch):
    monkeypatch.setattr(main, "_check_retrieval_ready", lambda: (True, False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_health_degraded_when_chunks_missing(client, monkeypatch):
    monkeypatch.setattr(main, "_check_retrieval_ready", lambda: (False, False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded"}
