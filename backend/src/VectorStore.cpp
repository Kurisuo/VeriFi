#include "VectorStore.h"
#include <fstream>      // std::ifstream
#include <cmath>        // std::sqrt
#include <algorithm>    // std::sort, std::min
#include <json.hpp>
#include <cstdio>


//used once in the beginning to fill storage
bool VectorStore::load_from_jsonl(const std::string& filepath) {
    storage.clear(); //in case ran more than once

    std::string readText = "";
    std::ifstream myFile(filepath);
    
    //chcek if file opened successfully
    
    if (!myFile.is_open()){
        std::printf("Error: Stopped at attempted opening file.");
        return false;
    }
    int skipped {0};
    while(std::getline(myFile, readText)) {
        DocumentChunk chunk;

        if(readText == "") continue;
        
        try{
            nlohmann::json j = nlohmann::json::parse(readText);
            chunk.chunk_index = j["chunk_index"].get<int>();
            chunk.text = j["text"].get<std::string>();
            chunk.source_document = j["source_document"].get<std::string>();
            chunk.page_number = j["page_number"].get<int>();
            chunk.embedding = j["embedding"].get<std::vector<float>>();
    
            if (chunk.embedding.size() != static_cast<std::size_t>(expected_dim_)) {
                skipped++; 
                continue;
            }
    
            storage.push_back(chunk);

        } catch (const std::exception& e) {
            skipped++;
            continue;
        }
    }

    if (storage.empty()){ 
        printf("Failed on storage.empty()\n");
        return false;
    } 
    
    std::printf("Success. Total Lines Skipped: %d", skipped);

    return true; 
}

std::vector<SearchResult> VectorStore::search(
        const std::vector<float>& query_embedding, int top_k) const {
            
            if (query_embedding.empty()) return {};
            if (query_embedding.size() != static_cast<std::size_t>(expected_dim_)) return {};
            if (top_k <= 0) return {};
            if (storage.empty()) return {};

            //Storing the {score, index} pair inside a fector - naming it score_pair
            std::vector<std::pair<float, std::size_t>> score_pair;
            //reserving up to storage.size() in space
            score_pair.reserve(storage.size());

            for(std::size_t index = 0; index < storage.size(); ++index){ 
                //check if embedding empty, skip if true - skip if chunk not the same size as dim expected
                if (storage[index].embedding.empty()) continue;
                if (storage[index].embedding.size() != static_cast<std::size_t>(expected_dim_)) continue;

                float score = cosine_similarity(query_embedding, storage[index].embedding);
                score_pair.push_back(std::make_pair(score, index));
            
            }

            //lambda function for sorting by descending - sort<> defaults to ascends
            std::sort(score_pair.begin(), score_pair.end(), 
            [](const std::pair<float, std::size_t>& a, const std::pair<float, std::size_t>& b) {
                return a.first > b.first;
            });

            //remove later
            if(score_pair.size() > 2){
                if(!(score_pair[0].first > score_pair[1].first)){
                    std::printf("error in sorting...\nscore_pair[0] = %f !> score_pair[1] = %f\n",
                                score_pair[0].first, score_pair[1].first);
                }
            }

            int N = score_pair.size();
            int minChunks = std::min(top_k ,N);

            if(minChunks == 0) return {};

            std::vector<SearchResult> searchResult;
            searchResult.reserve(minChunks);

            for(int iter = 0; iter < minChunks; iter++){
            
                float score = score_pair[iter].first;
                std::size_t chunk_index = score_pair[iter].second;
                std::string docText = storage[chunk_index].text;
                std::string docSource = storage[chunk_index].source_document;
                int pageNum = storage[chunk_index].page_number;

                searchResult.push_back({score, docText, docSource, pageNum});
            }

    return searchResult;
}

//Get total chunks 
std::size_t VectorStore::fetchSize() const {
    return storage.size();
}

//Get width of embedding
int VectorStore::dimension() const {
    if (storage.empty()) return 0;
    return static_cast<int>(storage[0].embedding.size());
}

float VectorStore::magnitude(const std::vector<float>& vec) const {

    if (vec.empty()) return 0.0f;
    
    float squareSum {0.0f};

    for (std::size_t i {0}; i < vec.size(); i++) {
        squareSum += vec[i] * vec[i];
    } 

    return std::sqrt(squareSum);
}

float VectorStore::dotProduct(const std::vector<float>& vec1, const std::vector<float>& vec2) const {

        if (vec1.empty() || vec2.empty()) return 0.0f;
        //Update to disclude this chunk in order to avoid polluting data 
        if (vec1.size() != vec2.size()) return 0.0f;

        float dotProductSum {0};

        for (int i {0}; i < vec1.size(); i++) {
            dotProductSum += (vec1[i] * vec2[i]);
        }

        return dotProductSum;
    }

//Each vector has 384 dimensions
//We are generating a single float value PER query, -1 - 1 ranking  
// this value will be used to rank chunks, the higher the score the closer the chunk is to matching the user query 

float VectorStore::cosine_similarity(const std::vector<float>& queryFloat, const std::vector<float>& dataBaseFloat) const {

    const float queryMag = magnitude(queryFloat);
    const float dbMag = magnitude(dataBaseFloat);

    //return empty float
    if (queryMag == 0.0f || dbMag == 0.0f) return 0.0f;
    
    return dotProduct(queryFloat, dataBaseFloat) / (queryMag * dbMag); 
}
