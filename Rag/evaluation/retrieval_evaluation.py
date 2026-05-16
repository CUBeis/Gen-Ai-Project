import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CHROMA_PATH,
    COHERE_API_KEY,
    EMBEDDING_MODEL,
    RERANK_MODEL,
    RETRIEVE_TOP_K,
    FINAL_TOP_K,
    MMR_LAMBDA,
)

import numpy as np
import cohere
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi


# =========================================================
# Settings from config.py
# =========================================================
COLLECTION_NAME = "medical_rag"
EMBED_MODEL     = EMBEDDING_MODEL
RERANK_MODEL_NAME = RERANK_MODEL
TOP_K           = RETRIEVE_TOP_K
FINAL_TOP_K     = FINAL_TOP_K
MMR_LAMBDA      = MMR_LAMBDA


# =========================================================
# Test Dataset
# =========================================================
TEST_DATASET = [
    {"question": "What are the side effects of metformin?",        "relevant_entity": "metformin",       "entity_type": "drug"},
    {"question": "What are the symptoms of type 2 diabetes?",      "relevant_entity": "Type 2 diabetes", "entity_type": "disease"},
    {"question": "What drugs interact with warfarin?",             "relevant_entity": "warfarin",        "entity_type": None},
    {"question": "What are the treatment options for hypertension?","relevant_entity": "Hypertension",   "entity_type": None},
    {"question": "ما هي أعراض مرض السكري من النوع الثاني؟",       "relevant_entity": "Type 2 diabetes", "entity_type": "disease"},
]


# =========================================================
# Init
# =========================================================
def load_clients():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
    collection    = chroma_client.get_collection(COLLECTION_NAME)
    cohere_client = cohere.Client(COHERE_API_KEY)
    return collection, cohere_client


def embed_query(query, cohere_client):
    return cohere_client.embed(texts=[query], model=EMBED_MODEL, input_type="search_query").embeddings[0]


# =========================================================
# Metadata Filter
# =========================================================
def build_filter(entity_type=None, source_type=None):
    conditions = []
    if entity_type:
        conditions.append({"entity_type": {"$eq": entity_type}})
    if source_type:
        conditions.append({"source_type": {"$eq": source_type}})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


# =========================================================
# Semantic Retrieve
# =========================================================
def semantic_retrieve(query, collection, cohere_client, top_k=TOP_K, entity_type=None):
    query_embedding = embed_query(query, cohere_client)
    where           = build_filter(entity_type)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id":          results["ids"][0][i],
            "score":       round(1 - results["distances"][0][i], 4),
            "text":        results["documents"][0][i],
            "embedding":   results["embeddings"][0][i],
            "entity_name": results["metadatas"][0][i].get("entity_name"),
            "entity_type": results["metadatas"][0][i].get("entity_type"),
        })
    return chunks


# =========================================================
# Hybrid Retrieve
# =========================================================
def hybrid_retrieve(query, collection, cohere_client, top_k=TOP_K, entity_type=None, alpha=0.7):
    chunks      = semantic_retrieve(query, collection, cohere_client, top_k=top_k * 2, entity_type=entity_type)
    corpus      = [c["text"].lower().split() for c in chunks]
    bm25        = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_max    = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_norm   = bm25_scores / bm25_max

    for i, chunk in enumerate(chunks):
        chunk["bm25_score"]   = round(float(bm25_norm[i]), 4)
        chunk["hybrid_score"] = round(alpha * chunk["score"] + (1 - alpha) * float(bm25_norm[i]), 4)

    chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return chunks[:top_k]


# =========================================================
# MMR
# =========================================================
def mmr(chunks, query_embedding, top_k=FINAL_TOP_K, lambda_param=MMR_LAMBDA):
    if not chunks:
        return []

    query_vec  = np.array(query_embedding).reshape(1, -1)
    candidates = list(chunks)
    selected   = []

    while len(selected) < top_k and candidates:
        relevance_scores = []
        for c in candidates:
            doc_vec = np.array(c["embedding"]).reshape(1, -1)
            sim = float(np.dot(query_vec, doc_vec.T) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-9))
            relevance_scores.append(sim)

        redundancy_scores = []
        for c in candidates:
            if not selected:
                redundancy_scores.append(0.0)
            else:
                doc_vec = np.array(c["embedding"]).reshape(1, -1)
                max_sim = max(
                    float(np.dot(np.array(s["embedding"]).reshape(1, -1), doc_vec.T) /
                          (np.linalg.norm(s["embedding"]) * np.linalg.norm(doc_vec) + 1e-9))
                    for s in selected
                )
                redundancy_scores.append(max_sim)

        mmr_scores = [lambda_param * rel - (1 - lambda_param) * red for rel, red in zip(relevance_scores, redundancy_scores)]
        best_idx   = int(np.argmax(mmr_scores))
        selected.append(candidates.pop(best_idx))

    return selected


# =========================================================
# Rerank
# =========================================================
def rerank(query, chunks, cohere_client, top_k=FINAL_TOP_K):
    if not chunks:
        return []
    response = cohere_client.rerank(model=RERANK_MODEL_NAME, query=query, documents=[c["text"] for c in chunks], top_n=top_k)
    reranked = []
    for i, result in enumerate(response.results):
        chunk = chunks[result.index].copy()
        chunk["rerank_score"] = round(result.relevance_score, 4)
        chunk["rank"]         = i + 1
        reranked.append(chunk)
    return reranked


# =========================================================
# Full Pipeline
# =========================================================
def retrieve(query, collection, cohere_client, top_k=FINAL_TOP_K, entity_type=None):
    chunks          = hybrid_retrieve(query, collection, cohere_client, top_k=TOP_K, entity_type=entity_type)
    query_embedding = embed_query(query, cohere_client)
    chunks          = mmr(chunks, query_embedding, top_k=TOP_K)
    chunks          = rerank(query, chunks, cohere_client, top_k=top_k)
    for i, chunk in enumerate(chunks):
        chunk["rank"] = i + 1
    return chunks


# =========================================================
# Evaluate
# =========================================================
def run():
    collection, cohere_client = load_clients()

    print("\n" + "=" * 60)
    print("📡 Retrieval Evaluation (Hybrid + MMR + Rerank)")
    print("=" * 60)

    hit_rates   = []
    mrr_scores  = []
    ndcg_scores = []

    for item in TEST_DATASET:
        query           = item["question"]
        relevant_entity = item["relevant_entity"]
        entity_type     = item["entity_type"]

        chunks             = retrieve(query, collection, cohere_client, entity_type=entity_type)
        retrieved_entities = [c["entity_name"] for c in chunks]

        # Hit Rate
        hit = int(relevant_entity in retrieved_entities)
        hit_rates.append(hit)

        # MRR
        rr = 0.0
        for rank, entity in enumerate(retrieved_entities, 1):
            if entity == relevant_entity:
                rr = 1.0 / rank
                break
        mrr_scores.append(rr)

        # NDCG
        relevance   = [1 if e == relevant_entity else 0 for e in retrieved_entities]
        dcg         = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevance))
        idcg        = sum(1.0 / np.log2(i + 2) for i in range(min(sum(relevance), FINAL_TOP_K)))
        ndcg        = dcg / idcg if idcg > 0 else 0.0
        ndcg_scores.append(ndcg)

        print(f"\n  Q: {query[:55]}...")
        print(f"     Hit@{FINAL_TOP_K}: {hit} | MRR: {rr:.4f} | NDCG: {ndcg:.4f}")
        print(f"     Retrieved : {retrieved_entities}")

    print("\n" + "=" * 60)
    print("Averages:")
    print(f"   Hit_Rate@{FINAL_TOP_K} : {np.mean(hit_rates):.4f}")
    print(f"   MRR          : {np.mean(mrr_scores):.4f}")
    print(f"   NDCG         : {np.mean(ndcg_scores):.4f}")


if __name__ == "__main__":
    run()