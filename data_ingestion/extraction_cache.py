import json
import time
from pathlib import Path

try:
    from .jsonl_writer import write_json
    from .pdf_reader import extract_pdf_text
    from .versions import EXTRACTION_VERSION
except ImportError:
    from jsonl_writer import write_json
    from pdf_reader import extract_pdf_text
    from versions import EXTRACTION_VERSION


DEFAULT_CACHE_DIR = Path("output/cache/extracted_layouts")


def cache_path_for(fingerprint, cache_dir=DEFAULT_CACHE_DIR):
    return Path(cache_dir) / f"{EXTRACTION_VERSION}_{fingerprint}.json"


def _read_cached_pages(cache_path, fingerprint):
    with cache_path.open("r", encoding="utf-8") as file:
        cached = json.load(file)

    if not isinstance(cached, dict):
        raise ValueError("cache entry must be a JSON object")
    if cached.get("extraction_version") != EXTRACTION_VERSION:
        raise ValueError("cache extraction version does not match")
    if cached.get("source_fingerprint") != fingerprint:
        raise ValueError("cache fingerprint does not match")
    pages = cached.get("pages")
    if not isinstance(pages, list):
        raise ValueError("cache pages must be a list")
    if any(not isinstance(page, dict) for page in pages):
        raise ValueError("each cached page must be an object")
    if cached.get("page_count") != len(pages):
        raise ValueError("cache page count does not match cached pages")
    return pages


def load_or_extract_pdf_layout(
    pdf_path,
    fingerprint,
    cache_dir=DEFAULT_CACHE_DIR,
    extractor=extract_pdf_text,
):
    pdf_path = Path(pdf_path)
    cache_path = cache_path_for(fingerprint, cache_dir)
    lookup_started = time.perf_counter()
    invalid_reason = None

    if cache_path.exists():
        try:
            pages = _read_cached_pages(cache_path, fingerprint)
            return pages, {
                "source_document": pdf_path.name,
                "status": "hit",
                "cache_hit": True,
                "page_count": len(pages),
                "lookup_seconds": round(time.perf_counter() - lookup_started, 4),
                "extraction_seconds": 0.0,
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            invalid_reason = str(error)

    lookup_seconds = time.perf_counter() - lookup_started
    extraction_started = time.perf_counter()
    pages = extractor(str(pdf_path))
    extraction_seconds = time.perf_counter() - extraction_started
    write_json(
        {
            "extraction_version": EXTRACTION_VERSION,
            "source_document": pdf_path.name,
            "source_fingerprint": fingerprint,
            "page_count": len(pages),
            "pages": pages,
        },
        str(cache_path),
    )

    event = {
        "source_document": pdf_path.name,
        "status": "invalid" if invalid_reason else "miss",
        "cache_hit": False,
        "page_count": len(pages),
        "lookup_seconds": round(lookup_seconds, 4),
        "extraction_seconds": round(extraction_seconds, 4),
    }
    if invalid_reason:
        event["invalid_reason"] = invalid_reason
    return pages, event
