"""API bridge tests: POST /chat contract and error paths."""

import main


def test_api_chat_happy_path(client, monkeypatch, sample_raw_results, sample_sources):
    monkeypatch.setattr(main, "_retrieval_ready", True)
    monkeypatch.setattr(main.embedder, "embed_query", lambda q: [0.1] * 384)
    monkeypatch.setattr(main, "_run_search", lambda emb, top_k=5: sample_raw_results)
    monkeypatch.setattr(
        main,
        "generate_rag_response",
        lambda question, chunks: {"answer": "Grounded answer.", "sources": []},
    )

    response = client.post("/chat", json={"query": "What data is collected?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Grounded answer."
    assert body["sources"] == sample_sources
    for source in body["sources"]:
        assert set(source.keys()) == {"doc", "page", "snippet", "score"}


def test_api_chat_retrieval_not_ready(client, monkeypatch):
    monkeypatch.setattr(main, "_retrieval_ready", False)

    response = client.post("/chat", json={"query": "test"})

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "chunks file missing" in body["answer"]


def test_api_chat_retrieval_failure(client, monkeypatch):
    monkeypatch.setattr(main, "_retrieval_ready", True)

    def _fail(_query):
        raise RuntimeError("embed failed")

    monkeypatch.setattr(main.embedder, "embed_query", _fail)

    response = client.post("/chat", json={"query": "test"})

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert body["answer"].startswith("Retrieval failed:")


def test_api_chat_no_results(client, monkeypatch):
    monkeypatch.setattr(main, "_retrieval_ready", True)
    monkeypatch.setattr(main.embedder, "embed_query", lambda q: [0.1] * 384)
    monkeypatch.setattr(main, "_run_search", lambda emb, top_k=5: [])

    response = client.post("/chat", json={"query": "nothing here"})

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "No relevant passages found" in body["answer"]


def test_api_chat_llm_failure_keeps_sources(
    client, monkeypatch, sample_raw_results, sample_sources
):
    monkeypatch.setattr(main, "_retrieval_ready", True)
    monkeypatch.setattr(main.embedder, "embed_query", lambda q: [0.1] * 384)
    monkeypatch.setattr(main, "_run_search", lambda emb, top_k=5: sample_raw_results)

    def _fail(_question, _chunks):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(main, "generate_rag_response", _fail)

    response = client.post("/chat", json={"query": "test"})

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == sample_sources
    assert body["answer"].startswith("Answer generation failed:")


def test_api_chat_invalid_body(client):
    response = client.post("/chat", json={})

    assert response.status_code == 422
