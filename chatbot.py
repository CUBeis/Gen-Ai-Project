import requests
import cohere
import chromadb

from dataclasses import dataclass, field
from datetime import datetime
from chromadb.config import Settings


# =========================================================
# Load Configuration from config.py
# =========================================================
from config import (
    CHROMA_PATH,
    COHERE_API_KEY,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OPENROUTER_API_KEY,
    MAX_HISTORY_MESSAGES,
    RETRIEVE_TOP_K,
)

COLLECTION_NAME  = "medical_rag"

COHERE_MODEL     = EMBEDDING_MODEL
OPENROUTER_MODEL   = LLM_MODEL
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

TOP_K            = RETRIEVE_TOP_K
HISTORY_WINDOW   = MAX_HISTORY_MESSAGES


# =========================================================
# System Prompt
# =========================================================
SYSTEM_PROMPT = """
You are a clinical medical assistant AI (Nerve AI).

Your role is to answer medical questions accurately and safely
based ONLY on the provided context from trusted medical sources.

Rules:
- Answer based on the context only. Do not hallucinate.
- If the context does not contain enough information, say so clearly.
- Always recommend consulting a doctor for personal medical decisions.
- Be concise, clear, and professional.
- You have memory of the current conversation — use it to understand follow-up questions.
- If the question is in Arabic, answer in Arabic.
- If the question is in English, answer in English.
""".strip()


# =========================================================
# 1. ChatMessage
# =========================================================
@dataclass
class ChatMessage:
    role      : str
    content   : str
    sources   : list[dict] = field(default_factory=list)
    timestamp : str        = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def to_llm_format(self) -> dict:
        return {"role": self.role, "content": self.content}


# =========================================================
# 2. ChatHistory
# =========================================================
class ChatHistory:

    def __init__(self, window: int = HISTORY_WINDOW):
        self.messages : list[ChatMessage] = []
        self.window   : int               = window

    def add(self, message: ChatMessage):
        self.messages.append(message)

    def get_window(self) -> list[ChatMessage]:
        return self.messages[-self.window:]

    def to_llm_messages(self) -> list[dict]:
        return [m.to_llm_format() for m in self.get_window()]

    def get_last_n_as_text(self, n: int = 4) -> str:

        recent = self.messages[-n:] if len(self.messages) >= n else self.messages
        lines  = []
        for m in recent:
            role = "User" if m.role == "user" else "Assistant"
            lines.append(f"{role}: {m.content}")
        return "\n".join(lines)

    def clear(self):
        self.messages.clear()
        print("\n Chat history cleared.\n")

    def print_history(self):
        if not self.messages:
            print("\n No history yet.\n")
            return
        print(f"\n{'─' * 50}")
        print(f"Chat History ({len(self.messages)} messages)")
        print(f"{'─' * 50}")
        for msg in self.messages:
            role_label = "👤 You      " if msg.role == "user" else "🤖 Nerve AI"
            print(f"[{msg.timestamp}] {role_label} : {msg.content[:100]}")
            if msg.sources:
                src_names = ", ".join(
                    s["entity_name"] for s in msg.sources[:3] if s.get("entity_name")
                )
                print(f"             📚 Sources: {src_names}")
        print(f"{'─' * 50}\n")

    def __len__(self) -> int:
        return len(self.messages)


# =========================================================
# 3. Query Reformulation  
# =========================================================
def reformulate_query(query: str, history: ChatHistory) -> str:

    if not history.messages:
        return query

    recent_context = history.get_last_n_as_text(n=4)

    reformulation_prompt = f"""Given this conversation history:
{recent_context}

Rewrite the following question as a complete, standalone search query.
Replace any pronouns (it, they, its, their, this, that) with the actual medical entity from the conversation.
Return ONLY the rewritten question, nothing else. No explanation. No quotes.
If the question is already complete and clear, return it unchanged.
If the question is in Arabic, rewrite it in Arabic.

Question: {query}
Rewritten:"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type" : "application/json",
    }

    payload = {
        "model"      : OPENROUTER_MODEL,
        "messages"   : [{"role": "user", "content": reformulation_prompt}],
        "temperature": 0.0,
        "max_tokens" : 80,
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers = headers,
            json    = payload,
            timeout = 10,
        )
        response.raise_for_status()
        reformulated = response.json()["choices"][0]["message"]["content"].strip()

        if not reformulated or len(reformulated) > 300:
            return query

        return reformulated

    except Exception:
        return query


# =========================================================
# 4. RAG Functions
# =========================================================
def embed_query(query: str, cohere_client: cohere.Client) -> list[float]:
    response = cohere_client.embed(
        texts      = [query],
        model      = COHERE_MODEL,
        input_type = "search_query",
    )
    return response.embeddings[0]


def retrieve(
    query         : str,
    collection,
    cohere_client : cohere.Client,
    top_k         : int = TOP_K,
) -> list[dict]:
    query_embedding = embed_query(query, cohere_client)

    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "rank"        : i + 1,
            "score"       : round(1 - results["distances"][0][i], 4),
            "text"        : results["documents"][0][i],
            "entity_name" : results["metadatas"][0][i].get("entity_name"),
            "entity_type" : results["metadatas"][0][i].get("entity_type"),
            "source_type" : results["metadatas"][0][i].get("source_type"),
            "url"         : results["metadatas"][0][i].get("url"),
        })
    return chunks


def build_context(chunks: list[dict]) -> str:
    context = ""
    for chunk in chunks:
        context += (
            f"[Source: {chunk['entity_name']} "
            f"({chunk['entity_type']}) | "
            f"Score: {chunk['score']}]\n"
            f"{chunk['text']}\n\n"
        )
    return context.strip()


# =========================================================
# 5. LLM with History
# =========================================================
def call_llm_with_history(
    query   : str,
    context : str,
    history : ChatHistory,
) -> str:
    user_message = (
        f"Context from trusted medical sources:\n{context}\n\n"
        f"Question: {query}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history.to_llm_messages(),
        {"role": "user", "content": user_message},
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type" : "application/json",
    }

    payload = {
        "model"      : OPENROUTER_MODEL,
        "messages"   : messages,
        "temperature": 0.2,
        "max_tokens" : 1024,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers = headers,
        json    = payload,
        timeout = 30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# =========================================================
# 6. ClinicalChatbot
# =========================================================
class ClinicalChatbot:
    """
    الـ chatbot الرئيسي. جاهز للـ import في FastAPI أو Streamlit.

    Example:
        bot = ClinicalChatbot()
        result = bot.chat("What are the side effects of metformin?")
        print(result["answer"])
        print(result["reformulated_query"])
    """

    def __init__(self, top_k: int = TOP_K, history_window: int = HISTORY_WINDOW):
        print("🚀 Initializing Nerve AI Clinical Chatbot...")

        chroma_client   = chromadb.PersistentClient(
            path     = CHROMA_PATH,
            settings = Settings(anonymized_telemetry=False),
        )
        self.collection = chroma_client.get_collection(COLLECTION_NAME)
        self.cohere     = cohere.Client(COHERE_API_KEY)
        self.top_k      = top_k
        self.history    = ChatHistory(window=history_window)

        print("Ready! ChromaDB + Cohere loaded.\n")

    def chat(self, query: str) -> dict:


        # Step 1: Reformulate
        reformulated = reformulate_query(query, self.history)

        # Step 2: Retrieve 
        chunks  = retrieve(reformulated, self.collection, self.cohere, self.top_k)

        # Step 3: Build context
        context = build_context(chunks)

        # Step 4: LLM + history
        answer  = call_llm_with_history(query, context, self.history)

        # Step 5: Save to history
        self.history.add(ChatMessage(role="user", content=query))
        self.history.add(ChatMessage(
            role    = "assistant",
            content = answer,
            sources = [
                {
                    "entity_name": c["entity_name"],
                    "entity_type": c["entity_type"],
                    "score"      : c["score"],
                    "url"        : c["url"],
                }
                for c in chunks
            ],
        ))

        return {
            "query"             : query,
            "reformulated_query": reformulated,
            "answer"            : answer,
            "sources"           : self.history.messages[-1].sources,
            "history_size"      : len(self.history),
        }

    def reset(self):
        self.history.clear()

    def show_history(self):
        self.history.print_history()


# =========================================================
# 7. Pretty Print
# =========================================================
def print_result(result: dict):
    print(f"\n{'═' * 60}")
    print(f"🔍  Original    : {result['query']}")

    if result["reformulated_query"] != result["query"]:
        print(f"🔄  Reformulated: {result['reformulated_query']}")

    print(f"  History     : {result['history_size']} messages")
    print(f"{'═' * 60}")
    print(f"\n  Answer:\n{result['answer']}")
    print(f"\n  Sources:")
    for s in result["sources"]:
        print(f"    • {s['entity_name']} ({s['entity_type']}) | score: {s['score']}")
    print()


# =========================================================
# 8. CLI Loop
# =========================================================
def run_cli():
    bot = ClinicalChatbot()

    print("=" * 60)
    print("🩺  Nerve AI — Clinical RAG Chatbot")
    print("=" * 60)
    print("Commands: /history | /reset | /quit\n")

    while True:
        try:
            query = input("👤 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            break

        if not query:
            continue

        if query == "/quit":
            print("\n👋 Goodbye!")
            break
        if query == "/history":
            bot.show_history()
            continue
        if query == "/reset":
            bot.reset()
            continue

        print("\n⏳ Thinking...\n")
        try:
            result = bot.chat(query)
            print_result(result)
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    run_cli()