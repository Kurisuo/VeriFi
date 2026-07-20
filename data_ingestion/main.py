import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .chunker import chunk_pages
    from .embedder import add_embeddings
    from .jsonl_writer import write_json, write_jsonl
    from .pdf_reader import extract_pdf_text
    from .semantic_chunker import semantic_chunk_pages
except ImportError:
    from chunker import chunk_pages
    from embedder import add_embeddings
    from jsonl_writer import write_json, write_jsonl
    from pdf_reader import extract_pdf_text
    from semantic_chunker import semantic_chunk_pages


SOURCE_DIR = Path("source_files")
OUTPUT_PATH = Path("output/chunks.jsonl")
LAYOUT_OUTPUT_PATH = Path("output/layout_chunks.jsonl")
STATS_PATH = Path("output/ingestion_stats.json")


def find_pdf_files(source_dir=SOURCE_DIR):
    return sorted(source_dir.glob("*.pdf"))


def source_fingerprint(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_documents(pdf_files):
    documents = []
    total_pages = 0
    for pdf_path in pdf_files:
        pages = extract_pdf_text(str(pdf_path))
        total_pages += len(pages)
        documents.append((pdf_path, pages, source_fingerprint(pdf_path)))
    return documents, total_pages


def _renumber(records):
    for chunk_index, chunk in enumerate(records):
        chunk["chunk_index"] = chunk_index
    return records


def build_layout_records(documents):
    records = []
    for pdf_path, pages, fingerprint in documents:
        records.extend(
            chunk_pages(
                pages,
                source_document=pdf_path.name,
                source_fingerprint=fingerprint,
            )
        )
    return _renumber(records)


def build_semantic_records(documents):
    records = []
    for pdf_path, pages, fingerprint in documents:
        records.extend(
            semantic_chunk_pages(
                pages,
                source_document=pdf_path.name,
                source_fingerprint=fingerprint,
            )
        )
    return _renumber(records)


def build_chunk_records(pdf_files):
    documents, total_pages = extract_documents(pdf_files)
    return build_semantic_records(documents), total_pages


def run_pipeline(pdf_files):
    pipeline_started = time.perf_counter()
    timings = {}

    stage_started = time.perf_counter()
    print("Stage: extracting PDF layout", flush=True)
    documents, total_pages = extract_documents(pdf_files)
    timings["extraction_seconds"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    print("Stage: building layout chunks", flush=True)
    layout_chunks = build_layout_records(documents)
    timings["layout_chunking_seconds"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    print("Stage: building semantic chunks", flush=True)
    semantic_chunks = build_semantic_records(documents)
    timings["semantic_chunking_seconds"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    print("Stage: generating embeddings", flush=True)
    semantic_chunks = add_embeddings(semantic_chunks)
    timings["embedding_seconds"] = time.perf_counter() - stage_started

    stage_started = time.perf_counter()
    print("Stage: writing outputs", flush=True)
    write_jsonl(layout_chunks, str(LAYOUT_OUTPUT_PATH))
    write_jsonl(semantic_chunks, str(OUTPUT_PATH))
    timings["write_seconds"] = time.perf_counter() - stage_started
    timings["total_seconds"] = time.perf_counter() - pipeline_started

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": len(pdf_files),
        "pages": total_pages,
        "layout_chunks": len(layout_chunks),
        "semantic_chunks": len(semantic_chunks),
        "timings": {key: round(value, 4) for key, value in timings.items()},
    }
    write_json(stats, str(STATS_PATH))
    return stats


def main():
    pdf_files = find_pdf_files()

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {SOURCE_DIR}")

    stats = run_pipeline(pdf_files)

    print(f"Documents: {stats['documents']}")
    print(f"Pages: {stats['pages']}")
    print(f"Layout chunks: {stats['layout_chunks']}")
    print(f"Semantic chunks: {stats['semantic_chunks']}")
    for name, seconds in stats["timings"].items():
        print(f"{name}: {seconds:.4f}")
    print(f"Layout output written to: {LAYOUT_OUTPUT_PATH}")
    print(f"Semantic output written to: {OUTPUT_PATH}")
    print(f"Runtime stats written to: {STATS_PATH}")


if __name__ == "__main__":
    main()
