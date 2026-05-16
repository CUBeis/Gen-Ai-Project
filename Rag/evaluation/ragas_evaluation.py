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

COLLECTION_NAME    = "medical_rag"
EMBED_MODEL        = EMBEDDING_MODEL
RERANK_MODEL_NAME  = RERANK_MODEL
OPENROUTER_MODEL   = LLM_MODEL
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
TOP_K              = RETRIEVE_TOP_K

SYSTEM_PROMPT = """
You are a clinical medical assistant AI.
Answer based ONLY on the provided context from trusted medical sources.
If the context does not contain enough information, say: "I don't have enough information."
Never hallucinate. Be concise and professional.
If the question is in Arabic, answer in Arabic.
""".strip()

RAGAS_EVAL_PROMPT = """
You are an evaluation assistant. Answer ONLY in the exact JSON format requested.
"""


# =========================================================
# Test Dataset
# =========================================================
TEST_DATASET = [
    {
        "question":     "What are the side effects of metformin?",
        "ground_truth": "The most common side effects of metformin include diarrhea, nausea, vomiting, flatulence, abdominal discomfort, indigestion, and headache.",
        "entity_type":  "drug",
    },
    {
        "question":     "What are the symptoms of type 2 diabetes?",
        "ground_truth": "Common symptoms of type 2 diabetes include increased thirst, frequent urination, fatigue, unexplained weight loss, blurred vision, and slow-healing wounds.",
        "entity_type":  "disease",
    },
    {
        "question":     "What drugs interact with warfarin?",
        "ground_truth": "Warfarin interacts with NSAIDs like naproxen and ibuprofen, which can increase bleeding risk.",
        "entity_type":  None,
    },
    {
        "question":     "What are the treatment options for hypertension?",
        "ground_truth": "Hypertension treatment includes lifestyle changes and medications such as thiazide diuretics, calcium channel blockers, ACE inhibitors, and ARBs.",
        "entity_type":  None,
    },
    {
        "question":     "ما هي أعراض مرض السكري من النوع الثاني؟",
        "ground_truth": "تشمل أعراض السكري من النوع الثاني العطش الشديد، التبول المتكرر، التعب، فقدان الوزن غير المبرر.",
        "entity_type":  "disease",
    },
]


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
# OpenRouter helper (sync, used for both RAG + eval)
# =========================================================
def call_llm(system: str, user: str, temperature=0.1, max_tokens=512) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# =========================================================
# Retrieval Helpers
# =========================================================
def embed_query(query, cohere_client):
    return cohere_client.embed(
        texts=[query],
        model=EMBED_MODEL,
        input_type="search_query"
    ).embeddings[0]


def semantic_retrieve(query, collection, cohere_client, top_k, entity_type=None):
    where   = {"entity_type": {"$eq": entity_type}} if entity_type else None
    results = collection.query(
        query_embeddings=[embed_query(query, cohere_client)],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id":        results["ids"][0][i],
            "score":     round(1 - results["distances"][0][i], 4),
            "text":      results["documents"][0][i],
            "embedding": results["embeddings"][0][i],
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
        rel_scores = [
            float(
                np.dot(query_vec, np.array(c["embedding"]).reshape(1, -1).T).item() /
                (np.linalg.norm(query_vec) * np.linalg.norm(c["embedding"]) + 1e-9)
            )
            for c in candidates
        ]
        red_scores = [
            max(
                [
                    float(
                        np.dot(np.array(s["embedding"]).reshape(1, -1), np.array(c["embedding"]).reshape(1, -1).T).item() /
                        (np.linalg.norm(s["embedding"]) * np.linalg.norm(c["embedding"]) + 1e-9)
                    )
                    for s in selected
                ],
                default=0.0
            )
            for c in candidates
        ]
        mmr_scores = [lambda_param * r - (1 - lambda_param) * d for r, d in zip(rel_scores, red_scores)]
        selected.append(candidates.pop(int(np.argmax(mmr_scores))))
    return selected


def rerank(query, chunks, cohere_client, top_k):
    response = cohere_client.rerank(
        model=RERANK_MODEL,
        query=query,
        documents=[c["text"] for c in chunks],
        top_n=top_k,
    )
    return [
        dict(**chunks[r.index], rerank_score=round(r.relevance_score, 4))
        for r in response.results
    ]


def retrieve(query, collection, cohere_client, top_k=FINAL_TOP_K, entity_type=None):
    chunks          = hybrid_retrieve(query, collection, cohere_client, top_k=TOP_K, entity_type=entity_type)
    query_embedding = embed_query(query, cohere_client)
    chunks          = mmr(chunks, query_embedding, top_k=TOP_K)
    return rerank(query, chunks, cohere_client, top_k=top_k)


def generate_answer(query, contexts):
    return call_llm(
        system=SYSTEM_PROMPT,
        user=f"Context:\n{chr(10).join(contexts)}\n\nQuestion: {query}",
    )


# =========================================================
# Manual RAGAS-style Metrics (sync, no ragas evaluate)
# =========================================================
def score_faithfulness(question, answer, contexts) -> float:
    """Are all claims in the answer supported by the context?"""
    import json
    ctx = "\n---\n".join(contexts)
    prompt = f"""Given the context and answer below, list each factual claim in the answer,
then judge if it is supported by the context (YES/NO).
Return JSON: {{"claims": [{{"claim": "...", "supported": true/false}}]}}

Context:
{ctx}

Answer:
{answer}

Return ONLY valid JSON, no extra text."""
    try:
        raw = call_llm(RAGAS_EVAL_PROMPT, prompt, temperature=0, max_tokens=800)
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        claims = data.get("claims", [])
        if not claims:
            return 1.0
        return round(sum(1 for c in claims if c.get("supported")) / len(claims), 4)
    except Exception:
        return float("nan")


def score_answer_relevancy(question, answer) -> float:
    """Does the answer address the question?"""
    import json
    prompt = f"""Rate how relevant the answer is to the question on a scale of 0.0 to 1.0.
1.0 = perfectly relevant, 0.0 = completely irrelevant.
Return JSON: {{"score": <float>}}

Question: {question}
Answer: {answer}

Return ONLY valid JSON, no extra text."""
    try:
        raw = call_llm(RAGAS_EVAL_PROMPT, prompt, temperature=0, max_tokens=100)
        raw = raw.replace("```json", "").replace("```", "").strip()
        return round(float(json.loads(raw)["score"]), 4)
    except Exception:
        return float("nan")


def score_context_precision(question, contexts, ground_truth) -> float:
    """Are the retrieved contexts relevant to the question?"""
    import json
    scores = []
    for ctx in contexts:
        prompt = f"""Is the following context relevant and useful for answering the question?
Return JSON: {{"relevant": true/false}}

Question: {question}
Context: {ctx}

Return ONLY valid JSON, no extra text."""
        try:
            raw = call_llm(RAGAS_EVAL_PROMPT, prompt, temperature=0, max_tokens=50)
            raw = raw.replace("```json", "").replace("```", "").strip()
            scores.append(1.0 if json.loads(raw).get("relevant") else 0.0)
        except Exception:
            scores.append(float("nan"))
    valid = [s for s in scores if not np.isnan(s)]
    return round(sum(valid) / len(valid), 4) if valid else float("nan")


def score_context_recall(question, contexts, ground_truth) -> float:
    """Does the context contain the information needed to answer correctly?"""
    import json
    ctx = "\n---\n".join(contexts)
    prompt = f"""Given the ground truth answer and the retrieved context, what fraction of the
ground truth information is covered by the context?
Return JSON: {{"score": <float between 0 and 1>}}

Ground Truth: {ground_truth}
Context: {ctx}

Return ONLY valid JSON, no extra text."""
    try:
        raw = call_llm(RAGAS_EVAL_PROMPT, prompt, temperature=0, max_tokens=100)
        raw = raw.replace("```json", "").replace("```", "").strip()
        return round(float(json.loads(raw)["score"]), 4)
    except Exception:
        return float("nan")


# =========================================================
# Evaluate
# =========================================================
def run():
    collection, cohere_client = load_clients()

    print("\n" + "=" * 60)
    print("🔬 RAGAS Evaluation (Hybrid + MMR + Rerank)")
    print("=" * 60)

    rows = []

    for i, item in enumerate(TEST_DATASET, 1):
        query        = item["question"]
        ground_truth = item["ground_truth"]
        entity_type  = item["entity_type"]

        print(f"\n  [{i}/{len(TEST_DATASET)}] {query[:60]}")

        chunks   = retrieve(query, collection, cohere_client, entity_type=entity_type)
        contexts = [c["text"] for c in chunks]
        answer   = generate_answer(query, contexts)

        print(f"    → answer generated, scoring...")

        faith   = score_faithfulness(query, answer, contexts)
        rel     = score_answer_relevancy(query, answer)
        prec    = score_context_precision(query, contexts, ground_truth)
        recall  = score_context_recall(query, contexts, ground_truth)

        print(f"    faithfulness={faith:.2f}  relevancy={rel:.2f}  precision={prec:.2f}  recall={recall:.2f}")

        rows.append({
            "question":         query,
            "answer":           answer,
            "ground_truth":     ground_truth,
            "faithfulness":     faith,
            "answer_relevancy": rel,
            "context_precision":prec,
            "context_recall":   recall,
        })

    import pandas as pd
    df = pd.DataFrame(rows)

    print("\n" + "=" * 60)
    print("RAGAS Averages:")
    print(f"   Faithfulness      : {df['faithfulness'].mean():.4f}")
    print(f"   Answer Relevancy  : {df['answer_relevancy'].mean():.4f}")
    print(f"   Context Precision : {df['context_precision'].mean():.4f}")
    print(f"   Context Recall    : {df['context_recall'].mean():.4f}")

    df.to_csv("ragas_results.csv", index=False)
    print("\nSaved to: ragas_results.csv")



# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    run()
