"""Shared fixtures for API_Tests (Ethan — API bridge)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

API_TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = API_TESTS_DIR.parent
BACKEND_SRC = BACKEND_DIR / "src"
REPO_ROOT = BACKEND_DIR.parent
PROMPTS_DIR = REPO_ROOT / "prompts"

for path in (str(BACKEND_SRC), str(BACKEND_DIR), str(PROMPTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Avoid loading torch/sentence-transformers when importing main.
if "sentence_transformers" not in sys.modules:
    _mock_st = MagicMock()
    _mock_st.SentenceTransformer = MagicMock()
    sys.modules["sentence_transformers"] = _mock_st

import main  # noqa: E402


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def sample_raw_results():
    return [
        {
            "score": 0.92,
            "text": "Minors may hold a custodial account.",
            "source_document": "privacy.pdf",
            "page_number": 2,
        },
        {
            "score": 0.81,
            "text": "Personal data is collected as described.",
            "source_document": "privacy.pdf",
            "page_number": 1,
        },
    ]


@pytest.fixture
def sample_sources(sample_raw_results):
    return main.mapper.to_sources(sample_raw_results)
