"""API bridge tests: search_cli subprocess adapter."""

import json
from unittest.mock import MagicMock

import pytest

from retrieval import vector_client
from retrieval.vector_client import VectorSearchError


def test_api_vector_client_parses_valid_json(monkeypatch, tmp_path):
    cli = tmp_path / "search_cli"
    cli.write_text("")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")

    payload = [{"score": 0.9, "text": "t", "source_document": "d.pdf", "page_number": 1}]
    completed = MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(vector_client, "SEARCH_CLI_PATH", cli)
    monkeypatch.setattr(vector_client, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("retrieval.vector_client.subprocess.run", lambda *a, **k: completed)

    results = vector_client.search([0.1] * 384, top_k=1)

    assert results == payload


def test_api_vector_client_empty_stdout(monkeypatch, tmp_path):
    cli = tmp_path / "search_cli"
    cli.write_text("")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")
    completed = MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(vector_client, "SEARCH_CLI_PATH", cli)
    monkeypatch.setattr(vector_client, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("retrieval.vector_client.subprocess.run", lambda *a, **k: completed)

    assert vector_client.search([0.1] * 384) == []


def test_api_vector_client_strips_junk_before_json(monkeypatch, tmp_path):
    cli = tmp_path / "search_cli"
    cli.write_text("")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")
    payload = [{"score": 0.5, "text": "x", "source_document": "a.pdf", "page_number": 1}]
    stdout = "Success. Total Lines Skipped: 0" + json.dumps(payload)
    completed = MagicMock(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(vector_client, "SEARCH_CLI_PATH", cli)
    monkeypatch.setattr(vector_client, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("retrieval.vector_client.subprocess.run", lambda *a, **k: completed)

    results = vector_client.search([0.1] * 384)

    assert results == payload


def test_api_vector_client_nonzero_exit(monkeypatch, tmp_path):
    cli = tmp_path / "search_cli"
    cli.write_text("")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")
    completed = MagicMock(returncode=1, stdout="", stderr="load failed")

    monkeypatch.setattr(vector_client, "SEARCH_CLI_PATH", cli)
    monkeypatch.setattr(vector_client, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("retrieval.vector_client.subprocess.run", lambda *a, **k: completed)

    with pytest.raises(VectorSearchError, match="exited with code 1"):
        vector_client.search([0.1] * 384)


def test_api_vector_client_invalid_json(monkeypatch, tmp_path):
    cli = tmp_path / "search_cli"
    cli.write_text("")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("{}\n")
    completed = MagicMock(returncode=0, stdout="not json", stderr="diag")

    monkeypatch.setattr(vector_client, "SEARCH_CLI_PATH", cli)
    monkeypatch.setattr(vector_client, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("retrieval.vector_client.subprocess.run", lambda *a, **k: completed)

    with pytest.raises(VectorSearchError, match="invalid JSON"):
        vector_client.search([0.1] * 384)
