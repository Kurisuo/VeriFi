# Data Ingestion

Data ingestion is Role 1 of VeriFi. It turns verified Fidelity PDFs into chunk records that Role 2 can load into the vector store.

Current pipeline:

```text
PDF files -> layout blocks -> semantic units -> semantic chunks -> embeddings -> JSONL
```

Generated handoff file:

```text
output/chunks.jsonl
```

Comparison and runtime artifacts:

```text
output/layout_chunks.jsonl
output/ingestion_stats.json
```

## Quick Start

Run these commands from the repo root:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python data_ingestion/main.py
```

If `.venv` does not exist yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data_ingestion/main.py
```

Expected output for the current sample PDF set:

```text
Layout chunks: 612
Semantic chunks: 580
total_seconds: 16.2311
Layout output written to: output/layout_chunks.jsonl
Semantic output written to: output/chunks.jsonl
Runtime stats written to: output/ingestion_stats.json
```

The first run may take longer because Sentence Transformers downloads the embedding model.

## Input Documents

Put verified Fidelity PDFs directly in:

```text
source_files/
```

The pipeline automatically processes every `.pdf` file directly inside `source_files/`. Files are processed in sorted filename order so output is deterministic.

Current source files:

```text
source_files/brokerage-account-customer-agreement.pdf
source_files/terms-and-conditions.pdf
source_files/privacy.pdf
```

## What Role 2 Should Use

Role 2 should read:

```text
output/chunks.jsonl
```

This is a JSONL file, not a normal JSON array. Each line is one independent JSON object.

Correct loading approach:

1. Open `output/chunks.jsonl`.
2. Read one line at a time.
3. Parse that line as JSON.
4. Store the parsed chunk in the vector database.
5. Use `embedding` for similarity search. It is generated from `embedding_text`.
6. Keep `text`, `source_document`, and `page_number` for answer context and citations.

Do not parse the entire file as one JSON object.

## Output Schema

Each line has this shape:

```json
{
  "chunk_index": 0,
  "chunk_id": "01a8f62ce2eb07f2990cf02d",
  "text": "TERMS AND CONDITIONS\n\nFor purposes of these Terms and Conditions...",
  "embedding_text": "Terms > TERMS AND CONDITIONS\n\nFor purposes of these Terms and Conditions...",
  "source_document": "terms-and-conditions.pdf",
  "page_number": 1,
  "page_start": 1,
  "page_end": 1,
  "page_numbers": [1],
  "section_title": "TERMS AND CONDITIONS",
  "section_path": ["Terms", "TERMS AND CONDITIONS"],
  "block_types": ["heading", "paragraph"],
  "semantic_unit_types": ["paragraph"],
  "token_count": 145,
  "embedding_max_tokens": 256,
  "source_fingerprint": "sha256...",
  "extraction_version": "layout-v2",
  "chunking_version": "semantic-v1",
  "embedding": [0.0267649535, -0.0358008891, -0.072021015]
}
```

Field contract:

| Field | Type | Meaning |
| --- | --- | --- |
| `chunk_id` | string | Stable content/position ID for deduping and traceability |
| `chunk_index` | integer | Zero-based chunk ID in the combined output file |
| `text` | string | Human-readable chunk text to use in RAG context |
| `embedding_text` | string | Section breadcrumb plus content used to generate the embedding |
| `source_document` | string | Original PDF filename |
| `page_number` | integer | One-based page number from the source PDF |
| `page_start` | integer | First page represented by the chunk |
| `page_end` | integer | Last page represented by the chunk |
| `page_numbers` | array of integers | All source pages represented by the chunk |
| `section_title` | string or null | Nearest detected section heading |
| `section_path` | array of strings | Hierarchical heading breadcrumb |
| `block_types` | array of strings | Layout block types in the chunk, such as `paragraph`, `heading`, `list`, or `table` |
| `semantic_unit_types` | array of strings | Semantic content types represented in the chunk |
| `token_count` | integer | Number of model tokens in `embedding_text` |
| `embedding_max_tokens` | integer | Maximum input length supported by the embedding model |
| `source_fingerprint` | string | SHA-256 fingerprint of the source PDF |
| `extraction_version` | string | Extraction/chunking version marker |
| `chunking_version` | string | Semantic chunking algorithm version |
| `embedding` | array of numbers | Vector representation of `embedding_text` |

Current embedding details:

| Property | Value |
| --- | --- |
| Model | `all-MiniLM-L6-v2` |
| Library | `sentence-transformers` |
| Vector length | `384` |
| Maximum input | `256` tokens, checked before embedding |

## Suggested Role 2 Data Shape

For the C++ vector-store role, the record maps naturally to a struct like:

```cpp
struct DocumentChunk {
    int chunk_index;
    std::string text;
    std::string source_document;
    int page_number;
    std::vector<float> embedding;
};
```

For retrieval, search over `embedding`. After finding matching chunks, return `text` plus citation metadata:

```text
source_document, page_number
```

Example citation display:

```text
terms-and-conditions.pdf, page 1
```

## Validate The JSONL

Use this from the repo root after running ingestion:

```bash
.venv/bin/python - <<'PY'
import json
from collections import Counter, defaultdict
from pathlib import Path

path = Path("output/chunks.jsonl")
records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
required = {
    "chunk_index",
    "chunk_id",
    "text",
    "embedding_text",
    "source_document",
    "page_number",
    "page_start",
    "page_end",
    "page_numbers",
    "section_title",
    "section_path",
    "block_types",
    "semantic_unit_types",
    "token_count",
    "embedding_max_tokens",
    "source_fingerprint",
    "extraction_version",
    "embedding",
}
pages_by_document = defaultdict(Counter)

for record in records:
    pages_by_document[record["source_document"]][record["page_number"]] += 1

print("records:", len(records))
print("missing required fields:", sum(1 for record in records if not required <= record.keys()))
print("empty text chunks:", sum(1 for record in records if not record["text"]))
print("contiguous chunk indexes:", [record["chunk_index"] for record in records] == list(range(len(records))))
print("unique chunk IDs:", len({record["chunk_id"] for record in records}) == len(records))
print("max text length:", max(len(record["text"]) for record in records))
print("documents:", dict(sorted(Counter(record["source_document"] for record in records).items())))
print("pages by document:", {doc: dict(sorted(pages.items())) for doc, pages in sorted(pages_by_document.items())})
print("embedding lengths:", dict(sorted(Counter(len(record["embedding"]) for record in records).items())))
print("all embedding values numeric:", all(isinstance(value, (int, float)) for record in records for value in record["embedding"]))
PY
```

Expected current validation:

```text
records: 580
missing required fields: 0
empty text chunks: 0
contiguous chunk indexes: True
unique chunk IDs: True
max text length: 900
documents: {'brokerage-account-customer-agreement.pdf': 533, 'privacy.pdf': 25, 'terms-and-conditions.pdf': 22}
embedding lengths: {384: 580}
all embedding values numeric: True
```

For the fuller quality gate, run:

```bash
.venv/bin/python data_ingestion/validator.py output/chunks.jsonl
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | No errors or warnings |
| `1` | Hard validation failure |
| `2` | Warnings found; usable but review recommended |

The chunk viewer exposes all three pipeline views and the latest per-stage runtime:

```text
http://127.0.0.1:8765/             # layout chunks
http://127.0.0.1:8765/semantic     # semantic chunks
http://127.0.0.1:8765/validated
```

## File Overview

| File | Purpose |
| --- | --- |
| `main.py` | Finds PDFs in `source_files/` and runs the complete ingestion pipeline |
| `pdf_reader.py` | Extracts layout-aware PDF blocks using PyMuPDF |
| `layout.py` | Defines layout block/page/section structures |
| `chunker.py` | Creates section-aware chunks with hard max-size enforcement |
| `semantic_chunker.py` | Creates hierarchical, sentence-safe semantic chunks and table-row groups |
| `embedder.py` | Adds `embedding` arrays using Sentence Transformers |
| `jsonl_writer.py` | Atomically writes JSONL outputs and runtime statistics |

## Format Stability

The existing fields should be treated as stable:

```text
chunk_index
text
source_document
page_number
embedding
```

Future changes should add new fields instead of renaming or removing these fields. This lets Role 2 keep the same parser and `DocumentChunk` structure.

## Known Limits

- The pipeline processes `.pdf` files directly inside `source_files/`; it does not recursively scan nested folders.
- Semantic chunking targets coherent sections and sentences, enforces a hard `900` character limit, and verifies that `embedding_text` stays within the model's `256`-token limit.
- Embeddings are generated locally with Sentence Transformers, not through an external API.
- The generated `output/chunks.jsonl` file can be recreated at any time by rerunning `python data_ingestion/main.py`.
