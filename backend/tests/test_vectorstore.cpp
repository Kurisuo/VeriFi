// Manual test driver for VectorStore.
// Build from backend/:
//   g++ -std=c++17 -Iinclude -Ilib src/VectorStore.cpp tests/test_vectorstore.cpp -o test_vs
// Run from backend/:
//   ./test_vs

#include <cassert>
#include <cmath>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <json.hpp>
#include "VectorStore.h"

namespace {

int failures = 0;

void check(bool condition, const std::string& message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        ++failures;
    }
}

void check_near(float actual, float expected, float epsilon, const std::string& message) {
    if (std::abs(actual - expected) > epsilon) {
        std::cerr << "FAIL: " << message << " (got " << actual << ", expected " << expected
                  << ")\n";
        ++failures;
    }
}

std::vector<float> load_embedding_from_jsonl(const std::string& filepath, int chunk_index) {
    std::ifstream file(filepath);
    std::string line;

    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }

        const nlohmann::json j = nlohmann::json::parse(line);
        if (j["chunk_index"].get<int>() == chunk_index) {
            return j["embedding"].get<std::vector<float>>();
        }
    }

    return {};
}

bool file_exists(const std::string& filepath) {
    std::ifstream file(filepath);
    return file.good();
}

std::string first_existing_path(const std::vector<std::string>& paths) {
    for (const std::string& path : paths) {
        if (file_exists(path)) {
            return path;
        }
    }
    return {};
}

bool matches_chunk(const SearchResult& result, int chunk_index, const std::string& jsonl_path) {
    std::ifstream file(jsonl_path);
    std::string line;

    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }

        const nlohmann::json j = nlohmann::json::parse(line);
        if (j["chunk_index"].get<int>() != chunk_index) {
            continue;
        }

        return result.text == j["text"].get<std::string>() &&
               result.source_document == j["source_document"].get<std::string>() &&
               result.page_number == j["page_number"].get<int>();
    }

    return false;
}

void test_search_guards_on_empty_store() {
    VectorStore store;
    std::vector<float> valid_query(384, 0.1f);

    check(store.search({}, 3).empty(), "empty query should return no results");
    check(store.search(valid_query, 0).empty(), "top_k <= 0 should return no results");
    check(store.search(valid_query, 3).empty(), "search on empty store should return no results");

    std::vector<float> wrong_dim(10, 0.1f);
    check(store.search(wrong_dim, 3).empty(), "wrong query dimension should return no results");
}

void test_load_failure_cases() {
    VectorStore store;
    check(!store.load_from_jsonl("this_file_does_not_exist.jsonl"),
          "missing file should fail to load");
    check(store.fetchSize() == 0, "failed load should leave storage empty");
}

void test_load_and_metadata(const std::string& jsonl_path) {
    VectorStore store;
    check(store.load_from_jsonl(jsonl_path), "load_from_jsonl should succeed");
    check(store.fetchSize() > 0, "storage should contain chunks after load");
    check(store.dimension() == 384, "dimension should be 384");
}

void test_self_retrieval(const std::string& jsonl_path, int chunk_index) {
    VectorStore store;
    if (!store.load_from_jsonl(jsonl_path)) {
        check(false, "load failed before self-retrieval test");
        return;
    }

    const std::vector<float> query = load_embedding_from_jsonl(jsonl_path, chunk_index);
    check(query.size() == 384, "test helper should load a 384-dim embedding");

    const std::vector<SearchResult> results = store.search(query, 3);
    check(!results.empty(), "self-retrieval should return at least one result");
    check_near(results[0].score, 1.0f, 1e-3f, "self-retrieval top score should be near 1.0");
    check(matches_chunk(results[0], chunk_index, jsonl_path),
          "top result should match the queried chunk metadata");
}

void test_top_k_limit(const std::string& jsonl_path) {
    VectorStore store;
    if (!store.load_from_jsonl(jsonl_path)) {
        check(false, "load failed before top_k test");
        return;
    }

    const std::vector<float> query = load_embedding_from_jsonl(jsonl_path, 0);
    const std::vector<SearchResult> results = store.search(query, 1);

    check(results.size() == 1, "top_k=1 should return exactly one result");
}

void test_sort_direction(const std::string& jsonl_path) {
    VectorStore store;
    if (!store.load_from_jsonl(jsonl_path)) {
        check(false, "load failed before sort-direction test");
        return;
    }

    const std::vector<float> query = load_embedding_from_jsonl(jsonl_path, 0);
    const std::vector<SearchResult> results = store.search(query, 3);

    check(results.size() >= 2, "need at least two results to verify sort direction");
    check(results[0].score >= results[1].score, "results should be sorted by descending score");
}

void test_optional_ingestion_file() {
    const std::string ingestion_path = first_existing_path({
        "output/chunks.jsonl",
        "../data_ingestion/output/chunks.jsonl",
    });

    if (ingestion_path.empty()) {
        std::cout << "SKIP: ingestion output/chunks.jsonl not found\n";
        return;
    }

    VectorStore store;
    check(store.load_from_jsonl(ingestion_path), "ingestion chunks.jsonl should load");
    check(store.fetchSize() >= 1, "ingestion file should contain chunks");
    check(store.dimension() == 384, "ingestion embeddings should be 384-dim");

    std::cout << "Loaded ingestion file: " << ingestion_path << '\n';
    std::cout << "chunks=" << store.fetchSize() << " dim=" << store.dimension() << '\n';
}

}  // namespace

int main() {
    const std::string fixture_path = first_existing_path({
        "tests/fixtures/test_chunks.jsonl",
        "backend/tests/fixtures/test_chunks.jsonl",
    });

    if (fixture_path.empty()) {
        std::cerr << "FAIL: could not find tests/fixtures/test_chunks.jsonl\n";
        return 1;
    }

    std::cout << "Using fixture: " << fixture_path << '\n';

    test_search_guards_on_empty_store();
    test_load_failure_cases();
    test_load_and_metadata(fixture_path);
    test_self_retrieval(fixture_path, 0);
    test_self_retrieval(fixture_path, 1);
    test_top_k_limit(fixture_path);
    test_sort_direction(fixture_path);
    test_optional_ingestion_file();

    if (failures > 0) {
        std::cerr << failures << " test(s) failed\n";
        return 1;
    }

    std::cout << "All tests passed\n";
    return 0;
}
