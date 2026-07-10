#pragma once
#include <string>
#include <vector>
#include "DocumentChunk.h"

// In-memory exact cosine-similarity k-NN store.
// Transport-agnostic on purpose: no HTTP, no networking, no JSON types in
// this interface — callers hand in plain C++ values and get plain C++ back.
class VectorStore {
public:
    VectorStore() = default;


    bool load_from_jsonl(const std::string& filepath);

    std::vector<SearchResult> search(const std::vector<float>& query_embedding,
                                     int top_k) const;


    std::size_t fetchSize() const;
    int dimension() const;

private:

    float cosine_similarity(const std::vector<float>& a, const std::vector<float>& b) const;
    float dotProduct(const std::vector<float>& vec1,
                     const std::vector<float>& vec2) const;
    float magnitude(const std::vector<float>& vec) const;

    //Stores all Chunks                        
    std::vector<DocumentChunk> storage;
    int expected_dim_ = 384;        // all-MiniLM-L6-v2 (ingestion's model)
};
