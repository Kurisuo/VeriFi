"""Optional API bridge integration test using fixture chunks (Python fallback)."""

import json
from pathlib import Path

import pytest

from retrieval import fallback_search

FIXTURE_CHUNKS = Path(__file__).resolve().parent / "fixtures" / "minimal_chunks.jsonl"


@pytest.mark.integration
def test_api_fallback_search_reads_fixture(monkeypatch):
    monkeypatch.setattr("retrieval.fallback_search.CHUNKS_PATH", FIXTURE_CHUNKS)

    # Fixture embeddings are length 3; query must match.
    results = fallback_search.search([0.1, 0.2, 0.0], top_k=2)

    assert len(results) >= 1
    assert results[0]["source_document"] == "privacy.pdf"
    assert "text" in results[0]
    assert "page_number" in results[0]
    assert "score" in results[0]


@pytest.mark.integration
def test_api_fixture_jsonl_is_valid():
    lines = FIXTURE_CHUNKS.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert "embedding" in record
        assert "source_document" in record
