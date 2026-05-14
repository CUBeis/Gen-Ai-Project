import json
import time

from pathlib import Path
import chromadb
from chromadb.config import Settings


# =========================================================
# Paths
# =========================================================
INPUT_PATH = Path("data/processed/embedded_chunks.json")
CHROMA_PATH = "./chroma_db"


# =========================================================
# Settings
# =========================================================
COLLECTION_NAME = "medical_rag"
BATCH_SIZE = 100


# =========================================================
# Load Client
# =========================================================
def load_client() -> chromadb.Client:

    print(f"📦 Loading ChromaDB from: {CHROMA_PATH}")

    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

    return client


# =========================================================
# Batch Generator
# =========================================================
def batchify(items, batch_size):

    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


# =========================================================
# Upload
# =========================================================
def upload():

    # =====================================================
    # Load chunks
    # =====================================================
    print(f"\n📂 Loading: {INPUT_PATH}")

    with open(INPUT_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"✅ Loaded {len(chunks)} chunks")

    # =====================================================
    # Init ChromaDB
    # =====================================================
    client = load_client()

    # Delete collection if exists (fresh start)
    existing = [c.name for c in client.list_collections()]

    if COLLECTION_NAME in existing:
        print(f"⚠️  Collection '{COLLECTION_NAME}' exists — deleting...")
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"✅ Collection '{COLLECTION_NAME}' created")

    # =====================================================
    # Upload in batches
    # =====================================================
    print(f"\n⚙️  Uploading {len(chunks)} chunks in batches of {BATCH_SIZE}...\n")

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    total_uploaded = 0

    for batch_index, batch in enumerate(batchify(chunks, BATCH_SIZE), start=1):

        ids         = [c["id"] for c in batch]
        embeddings  = [c["embedding"] for c in batch]
        documents   = [c["text"] for c in batch]

        metadatas = [
            {
                "source":       c.get("source", ""),
                "source_type":  c.get("source_type", ""),
                "entity_name":  c.get("entity_name") or "",
                "entity_type":  c.get("entity_type") or "",
                "url":          c.get("url") or "",
                "chunk_index":  c.get("chunk_index", 0),
                "total_chunks": c.get("total_chunks", 0),
            }
            for c in batch
        ]

        try:

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            total_uploaded += len(batch)

            print(f"  ✅ Batch {batch_index}/{total_batches} — {total_uploaded}/{len(chunks)}")

        except Exception as e:

            print(f"  ❌ Batch {batch_index} failed: {e}")

        time.sleep(0.1)

    # =====================================================
    # Stats
    # =====================================================
    print("\n" + "=" * 50)
    print(f"✅ Total uploaded : {total_uploaded}")
    print(f"📦 Collection     : {COLLECTION_NAME}")
    print(f"💾 Stored in      : {CHROMA_PATH}")


# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    upload()