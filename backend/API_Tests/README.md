# VeriFi API Bridge Tests (`API_Tests`)

**Owner:** Ethan (API / Backend Bridge)

Tests for the FastAPI contract (`GET /health`, `POST /chat`), retrieval adapters, and orchestration in `backend/src/main.py`.

**Out of scope:** C++ VectorStore math (`backend/tests/`), ingestion pipelines (repo-root `tests/`), prompt QA (`prompts/evaluation/`).

## Run

From repo root:

```bash
pytest backend/API_Tests -q
```

Skip optional integration tests:

```bash
pytest backend/API_Tests -q -m "not integration"
```

## Test overview

### `test_api_health.py` — `GET /health`

| Test | What it checks |
|------|----------------|
| `test_api_health_ok_when_chunks_present` | Returns `{"status": "ok"}` when chunks are available |
| `test_api_health_degraded_when_chunks_missing` | Returns `{"status": "degraded"}` when chunks are missing |

### `test_api_chat.py` — `POST /chat`

| Test | What it checks |
|------|----------------|
| `test_api_chat_happy_path` | Successful chat returns grounded `answer` and `sources` with `doc` / `page` / `snippet` / `score` |
| `test_api_chat_retrieval_not_ready` | Missing chunks file → empty sources and a clear unavailable message |
| `test_api_chat_retrieval_failure` | Embed/search errors → empty sources and a `Retrieval failed:` answer |
| `test_api_chat_no_results` | Zero search hits → empty sources and a no-passages message |
| `test_api_chat_llm_failure_keeps_sources` | LLM failure still returns retrieved sources with an generation-failed answer |
| `test_api_chat_invalid_body` | Missing `query` → HTTP 422 validation error |

### `test_api_mapper.py` — wire-format mapping

| Test | What it checks |
|------|----------------|
| `test_api_mapper_single_result` | C++ result maps to frontend `{doc, page, snippet, score}` |
| `test_api_mapper_preserves_order_and_types` | Multiple results keep order; page/score coerce to int/float |

### `test_api_vector_client.py` — `search_cli` adapter

| Test | What it checks |
|------|----------------|
| `test_api_vector_client_parses_valid_json` | Valid JSON array on stdout is returned as results |
| `test_api_vector_client_empty_stdout` | Empty stdout yields an empty list |
| `test_api_vector_client_strips_junk_before_json` | Diagnostic text before `[` is stripped so JSON still parses |
| `test_api_vector_client_nonzero_exit` | Non-zero exit raises `VectorSearchError` |
| `test_api_vector_client_invalid_json` | Bad stdout raises `VectorSearchError` mentioning invalid JSON |

### `test_api_chat_integration.py` — optional (`@pytest.mark.integration`)

| Test | What it checks |
|------|----------------|
| `test_api_fallback_search_reads_fixture` | Python fallback search reads `fixtures/minimal_chunks.jsonl` |
| `test_api_fixture_jsonl_is_valid` | Fixture JSONL lines parse and include required fields |
