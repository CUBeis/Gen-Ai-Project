import cohere
import chromadb
import numpy as np
import time

from chromadb.config import Settings
from rank_bm25 import BM25Okapi


# =========================================================
# Settings
# =========================================================
# =========================================================
# Load Configuration from config.py
# =========================================================
from config import (
    CHROMA_PATH,
    COHERE_API_KEY,
    EMBEDDING_MODEL,
    RERANK_MODEL,
    RETRIEVE_TOP_K,
    FINAL_TOP_K,
    MMR_LAMBDA,
    COLLECTION_NAME,
)

EMBED_MODEL = EMBEDDING_MODEL
RERANK_MODEL_NAME = RERANK_MODEL
TOP_K = RETRIEVE_TOP_K


# =========================================================
# Init Clients
# =========================================================
def load_clients():

    chroma_client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

    collection    = chroma_client.get_collection(COLLECTION_NAME)
    cohere_client = cohere.Client(COHERE_API_KEY)

    return collection, cohere_client


# =========================================================
# Embed Query
# =========================================================
def embed_query(query: str, cohere_client) -> list[float]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = cohere_client.embed(
                texts=[query],
                model=EMBED_MODEL,
                input_type="search_query",
            )
            return response.embeddings[0]
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ Connection error (embed), retrying in 2s... ({attempt+1}/{max_retries})")
                time.sleep(2)
            else:
                raise e


# =========================================================
# 1. Metadata Filters
# =========================================================
def build_filter(
    entity_type: str = None,
    source_type: str = None,
) -> dict | None:
    """
    entity_type : "disease" أو "drug"
    source_type : "disease_wiki" أو "drug_label"
    """

    conditions = []

    if entity_type:
        conditions.append({"entity_type": {"$eq": entity_type}})

    if source_type:
        conditions.append({"source_type": {"$eq": source_type}})

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


# =========================================================
# 2. Semantic Retrieval (base)
# =========================================================
def semantic_retrieve(
    query: str,
    collection,
    cohere_client,
    top_k: int = RETRIEVE_TOP_K,
    entity_type: str = None,
    source_type: str = None,
) -> list[dict]:

    query_embedding = embed_query(query, cohere_client)
    where           = build_filter(entity_type, source_type)

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
            "source_type": results["metadatas"][0][i].get("source_type"),
            "url":         results["metadatas"][0][i].get("url"),
        })

    return chunks


# =========================================================
# 3. Hybrid Retrieval (Semantic + BM25)
# =========================================================
def hybrid_retrieve(
    query: str,
    collection,
    cohere_client,
    top_k: int = TOP_K,
    entity_type: str = None,
    source_type: str = None,
    alpha: float = 0.7,   # 0 = BM25 فقط, 1 = Semantic فقط
) -> list[dict]:
    """
    alpha=0.7 → 70% semantic + 30% BM25
    """

    # --- Semantic scores ---
    semantic_chunks = semantic_retrieve(
        query, collection, cohere_client,
        top_k=top_k * 2,
        entity_type=entity_type,
        source_type=source_type,
    )

    # --- BM25 scores ---
    corpus     = [c["text"].lower().split() for c in semantic_chunks]
    bm25       = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(query.lower().split())

    # Normalize BM25 to [0, 1]
    bm25_max = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_norm = bm25_scores / bm25_max

    # --- Combine scores ---
    for i, chunk in enumerate(semantic_chunks):
        semantic_score = chunk["score"]
        bm25_score     = bm25_norm[i]
        chunk["bm25_score"]    = round(float(bm25_score), 4)
        chunk["hybrid_score"]  = round(
            alpha * semantic_score + (1 - alpha) * bm25_score, 4
        )

    # Sort by hybrid score
    semantic_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)

    return semantic_chunks[:top_k]


# =========================================================
# 4. MMR — Maximal Marginal Relevance
# =========================================================
def mmr(
    chunks: list[dict],
    query_embedding: list[float],
    top_k: int = FINAL_TOP_K,
    lambda_param: float = MMR_LAMBDA,
) -> list[dict]:
    """
    بيختار chunks متنوعة ومرتبطة بالسؤال في نفس الوقت.
    lambda_param:
        - قريب من 1 → relevance أكتر
        - قريب من 0 → diversity أكتر
    """

    if not chunks:
        return []

    query_vec  = np.array(query_embedding).reshape(1, -1)
    candidates = list(chunks)
    selected   = []

    while len(selected) < top_k and candidates:

        # Relevance: cosine similarity مع الـ query
        relevance_scores = []

        for c in candidates:
            doc_vec = np.array(c["embedding"]).reshape(1, -1)
            sim = float(
                np.dot(query_vec, doc_vec.T) /
                (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-9)
            )
            relevance_scores.append(sim)

        # Redundancy: cosine similarity مع الـ selected chunks
        if not selected:
            redundancy_scores = [0.0] * len(candidates)
        else:
            redundancy_scores = []
            for c in candidates:
                doc_vec = np.array(c["embedding"]).reshape(1, -1)
                max_sim = max(
                    float(
                        np.dot(np.array(s["embedding"]).reshape(1, -1), doc_vec.T) /
                        (np.linalg.norm(s["embedding"]) * np.linalg.norm(doc_vec) + 1e-9)
                    )
                    for s in selected
                )
                redundancy_scores.append(max_sim)

        # MMR Score
        mmr_scores = [
            lambda_param * rel - (1 - lambda_param) * red
            for rel, red in zip(relevance_scores, redundancy_scores)
        ]

        best_idx = int(np.argmax(mmr_scores))
        selected.append(candidates.pop(best_idx))

    return selected


# =========================================================
# 5. Reranking — Cohere Rerank
# =========================================================
def rerank(
    query: str,
    chunks: list[dict],
    cohere_client,
    top_k: int = FINAL_TOP_K,
) -> list[dict]:

    if not chunks:
        return []

    documents = [c["text"] for c in chunks]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = cohere_client.rerank(
                model=RERANK_MODEL_NAME,
                query=query,
                documents=documents,
                top_n=top_k,
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ Connection error (rerank), retrying in 2s... ({attempt+1}/{max_retries})")
                time.sleep(2)
            else:
                raise e

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
def retrieve(
    query: str,
    collection,
    cohere_client,
    top_k: int = FINAL_TOP_K,
    entity_type: str = None,
    source_type: str = None,
    use_hybrid: bool = True,
    use_mmr: bool = True,
    use_rerank: bool = True,
) -> list[dict]:
    """
    Full retrieval pipeline:
        1. Hybrid Retrieval (Semantic + BM25)
        2. MMR for diversity
        3. Cohere Rerank for final ranking
    """

    # Step 1: Hybrid or Semantic
    if use_hybrid:
        chunks = hybrid_retrieve(
            query, collection, cohere_client,
            top_k=RETRIEVE_TOP_K,
            entity_type=entity_type,
            source_type=source_type,
        )
    else:
        chunks = semantic_retrieve(
            query, collection, cohere_client,
            top_k=RETRIEVE_TOP_K,
            entity_type=entity_type,
            source_type=source_type,
        )

    # Step 2: MMR
    if use_mmr:
        query_embedding = embed_query(query, cohere_client)
        chunks = mmr(chunks, query_embedding, top_k=top_k)

    # Step 3: Rerank
    if use_rerank:
        chunks = rerank(query, chunks, cohere_client, top_k=top_k)

    # Add rank
    for i, chunk in enumerate(chunks):
        chunk["rank"] = i + 1

    return chunks


# =========================================================
# Pretty Print
# =========================================================
def print_results(query: str, chunks: list[dict]):

    print(f"\n{'=' * 60}")
    print(f"SEARCH Query: {query}")
    print(f"{'=' * 60}")

    for chunk in chunks:

        print(f"\nRANK Rank {chunk['rank']}")
        print(f"   Entity       : {chunk['entity_name']} ({chunk['entity_type']})")
        print(f"   Sem Score    : {chunk.get('score', 'N/A')}")
        print(f"   BM25 Score   : {chunk.get('bm25_score', 'N/A')}")
        print(f"   Hybrid Score : {chunk.get('hybrid_score', 'N/A')}")
        print(f"   Rerank Score : {chunk.get('rerank_score', 'N/A')}")
        print(f"   Text         : {chunk['text'][:250]}...")


# =========================================================
# Main
# =========================================================
def run():

    collection, cohere_client = load_clients()

    test_queries = [
        {
            "query": "What are the side effects of metformin?",
            "entity_type": "drug",
        },
        {
            "query": "ما هي أعراض مرض السكري من النوع الثاني؟",
            "entity_type": "disease",
        },
        {
            "query": "drug interactions with warfarin",
            "entity_type": None,
        },
        {
            "query": "hypertension treatment options",
            "entity_type": None,
        },
    ]

    for item in test_queries:

        chunks = retrieve(
            query=item["query"],
            collection=collection,
            cohere_client=cohere_client,
            entity_type=item.get("entity_type"),
            use_hybrid=True,
            use_mmr=True,
            use_rerank=True,
        )

        print_results(item["query"], chunks)


# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    run()