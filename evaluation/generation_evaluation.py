import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CHROMA_PATH,
    COHERE_API_KEY,
    EMBEDDING_MODEL,
    RERANK_MODEL,
    LLM_MODEL,
    OPENROUTER_API_KEY,
    RETRIEVE_TOP_K,
    FINAL_TOP_K,
    MMR_LAMBDA,
)

import numpy as np
import cohere
import chromadb
import requests

from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from bert_score import score as bert_score


# =========================================================
# Settings from config.py
# =========================================================
COLLECTION_NAME    = "medical_rag"
EMBED_MODEL        = EMBEDDING_MODEL
RERANK_MODEL_NAME  = RERANK_MODEL
OPENROUTER_MODEL   = LLM_MODEL
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
TOP_K              = RETRIEVE_TOP_K
FINAL_TOP_K        = FINAL_TOP_K
MMR_LAMBDA         = MMR_LAMBDA

SYSTEM_PROMPT = """
You are a clinical medical assistant AI.
Answer based ONLY on the provided context from trusted medical sources.
If the context does not contain enough information, say: "I don't have enough information."
Never hallucinate. Be concise and professional.
If the question is in Arabic, answer in Arabic.
""".strip()


# =========================================================
# Test Dataset
# =========================================================
TEST_DATASET = [
    {"question": "What are the side effects of metformin?",         "ground_truth": "The most common side effects of metformin include diarrhea, nausea, vomiting, flatulence, abdominal discomfort, indigestion, and headache.", "entity_type": "drug"},
    {"question": "What are the symptoms of type 2 diabetes?",       "ground_truth": "Common symptoms of type 2 diabetes include increased thirst, frequent urination, fatigue, unexplained weight loss, blurred vision, and slow-healing wounds.", "entity_type": "disease"},
    {"question": "What drugs interact with warfarin?",              "ground_truth": "Warfarin interacts with NSAIDs like naproxen and ibuprofen, which can increase bleeding risk.", "entity_type": None},
    {"question": "What are the treatment options for hypertension?", "ground_truth": "Hypertension treatment includes lifestyle changes and medications such as thiazide diuretics, calcium channel blockers, ACE inhibitors, and ARBs.", "entity_type": None},
    {"question": "ما هي أعراض مرض السكري من النوع الثاني؟",        "ground_truth": "تشمل أعراض السكري من النوع الثاني العطش الشديد، التبول المتكرر، التعب، فقدان الوزن غير المبرر.", "entity_type": "disease"},
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


def build_filter(entity_type=None):
    if not entity_type:
        return None
    return {"entity_type": {"$eq": entity_type}}


def semantic_retrieve(query, collection, cohere_client, top_k, entity_type=None):
    query_embedding = embed_query(query, cohere_client)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=build_filter(entity_type),
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id":        results["ids"][0][i],
            "score":     round(1 - results["distances"][0][i], 4),
            "text":      results["documents"][0][i],
            "embedding": results["embeddings"][0][i],
            "entity_name": results["metadatas"][0][i].get("entity_name"),
        })
    return chunks


def hybrid_retrieve(query, collection, cohere_client, top_k, entity_type=None, alpha=0.7):
    chunks      = semantic_retrieve(query, collection, cohere_client, top_k=top_k * 2, entity_type=entity_type)
    bm25        = BM25Okapi([c["text"].lower().split() for c in chunks])
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_max    = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_norm   = bm25_scores / bm25_max
    for i, chunk in enumerate(chunks):
        chunk["hybrid_score"] = round(alpha * chunk["score"] + (1 - alpha) * float(bm25_norm[i]), 4)
    chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return chunks[:top_k]


def mmr(chunks, query_embedding, top_k, lambda_param=MMR_LAMBDA):
    query_vec  = np.array(query_embedding).reshape(1, -1)
    candidates = list(chunks)
    selected   = []
    while len(selected) < top_k and candidates:
        rel_scores = [float(np.dot(query_vec, np.array(c["embedding"]).reshape(1, -1).T) / (np.linalg.norm(query_vec) * np.linalg.norm(c["embedding"]) + 1e-9)) for c in candidates]
        red_scores = [max([float(np.dot(np.array(s["embedding"]).reshape(1, -1), np.array(c["embedding"]).reshape(1, -1).T) / (np.linalg.norm(s["embedding"]) * np.linalg.norm(c["embedding"]) + 1e-9)) for s in selected], default=0.0) for c in candidates]
        mmr_scores = [lambda_param * r - (1 - lambda_param) * d for r, d in zip(rel_scores, red_scores)]
        selected.append(candidates.pop(int(np.argmax(mmr_scores))))
    return selected


def rerank(query, chunks, cohere_client, top_k):
    response = cohere_client.rerank(model=RERANK_MODEL_NAME, query=query, documents=[c["text"] for c in chunks], top_n=top_k)
    return [dict(**chunks[r.index], rerank_score=round(r.relevance_score, 4)) for r in response.results]


def retrieve(query, collection, cohere_client, top_k=FINAL_TOP_K, entity_type=None):
    chunks          = hybrid_retrieve(query, collection, cohere_client, top_k=TOP_K, entity_type=entity_type)
    query_embedding = embed_query(query, cohere_client)
    chunks          = mmr(chunks, query_embedding, top_k=TOP_K)
    return rerank(query, chunks, cohere_client, top_k=top_k)


def generate_answer(query, contexts):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{chr(10).join(contexts)}\n\nQuestion: {query}"},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# =========================================================
# Evaluate
# =========================================================
def run():
    collection, cohere_client = load_clients()

    print("\n" + "=" * 60)
    print("✍️  Generation Evaluation (Hybrid + MMR + Rerank)")
    print("=" * 60)

    scorer      = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    smoother    = SmoothingFunction().method1
    bleu_scores = []
    rouge1_list = []
    rougeL_list = []
    bert_preds  = []
    bert_refs   = []

    for item in TEST_DATASET:
        query        = item["question"]
        ground_truth = item["ground_truth"]
        entity_type  = item["entity_type"]

        chunks   = retrieve(query, collection, cohere_client, entity_type=entity_type)
        contexts = [c["text"] for c in chunks]
        answer   = generate_answer(query, contexts)

        bleu   = sentence_bleu([ground_truth.lower().split()], answer.lower().split(), smoothing_function=smoother)
        rouge  = scorer.score(ground_truth, answer)

        bleu_scores.append(bleu)
        rouge1_list.append(rouge["rouge1"].fmeasure)
        rougeL_list.append(rouge["rougeL"].fmeasure)
        bert_preds.append(answer)
        bert_refs.append(ground_truth)

        print(f"\n  Q: {query[:55]}...")
        print(f"  A: {answer[:100]}...")
        print(f"     BLEU: {bleu:.4f} | ROUGE-1: {rouge['rouge1'].fmeasure:.4f} | ROUGE-L: {rouge['rougeL'].fmeasure:.4f}")

    print("\n Computing BERTScore...")
    _, _, F1 = bert_score(bert_preds, bert_refs, lang="en", verbose=False)

    print("\n" + "=" * 60)
    print("Averages:")
    print(f"   BLEU      : {np.mean(bleu_scores):.4f}")
    print(f"   ROUGE-1   : {np.mean(rouge1_list):.4f}")
    print(f"   ROUGE-L   : {np.mean(rougeL_list):.4f}")
    print(f"   BERTScore : {F1.mean().item():.4f}")


if __name__ == "__main__":
    run()