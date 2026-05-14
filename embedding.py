import json
import time

from pathlib import Path
import cohere


# =========================================================
# Paths
# =========================================================
INPUT_PATH      = Path("data/processed/chunks.json")
OUTPUT_PATH     = Path("data/processed/embedded_chunks.json")
CHECKPOINT_PATH = Path("data/processed/embedded_chunks_checkpoint.json")


# =========================================================
# Load Configuration from config.py
# =========================================================
from config import (
    COHERE_API_KEY,
    EMBEDDING_MODEL,
    BATCH_SIZE,
    PROCESSED_DATA_DIR,
)

MODEL_NAME = EMBEDDING_MODEL

# =========================================================
# Rate-limit tuning
# =========================================================
# Delay between every successful batch (seconds).
# Increase this if you keep hitting 429s.
BATCH_DELAY      = 2.0   # seconds between batches
CHECKPOINT_EVERY = 10    # save progress every N batches
MAX_RETRIES      = 7     # max attempts per batch
INITIAL_BACKOFF  = 10    # seconds — first retry wait after 429
MAX_BACKOFF      = 120   # cap backoff at 2 minutes


# =========================================================
# Load Cohere Client
# =========================================================
def load_client() -> cohere.Client:
    print(f"🤖 Loading Cohere Model: {MODEL_NAME}")
    return cohere.Client(COHERE_API_KEY)


# =========================================================
# Batch Generator
# =========================================================
def batchify(items, batch_size):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


# =========================================================
# Embed a single batch with persistent backoff
# =========================================================
def embed_batch_with_retry(
    client,
    batch: list[str],
    batch_index: int,
    backoff_state: dict,   # {"delay": float} shared across batches
) -> list:

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.embed(
                texts=batch,
                model=MODEL_NAME,
                input_type="search_document",
            )
            # Success — slowly cool down the persistent backoff
            backoff_state["delay"] = max(
                BATCH_DELAY,
                backoff_state["delay"] * 0.75,
            )
            return response.embeddings

        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "rate limit" in err.lower() or "too many" in err.lower()

            if is_rate_limit:
                # Increase persistent backoff
                backoff_state["delay"] = min(backoff_state["delay"] * 2, MAX_BACKOFF)
                wait = backoff_state["delay"]
                print(
                    f"  ⚠️  Rate limit (Batch {batch_index}, attempt {attempt}/{MAX_RETRIES}). "
                    f"Waiting {wait:.0f}s ..."
                )
                time.sleep(wait)
            else:
                # Non-rate-limit error: fixed short retry
                print(f"  ❌  Batch {batch_index} error (attempt {attempt}/{MAX_RETRIES}): {e}")
                time.sleep(5)

    raise RuntimeError(f"Batch {batch_index} failed after {MAX_RETRIES} attempts.")


# =========================================================
# Generate Embeddings
# =========================================================
def embed_chunks():

    client = load_client()

    # =====================================================
    # Load chunks
    # =====================================================
    with open(INPUT_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    total_chunks = len(chunks)
    print(f"\n📦 Loaded {total_chunks} chunks")

    # =====================================================
    # Resume from checkpoint if available
    # =====================================================
    start_batch = 0
    all_embeddings: list = []

    if CHECKPOINT_PATH.exists():
        print(f"\n♻️  Checkpoint found: {CHECKPOINT_PATH}")
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            checkpoint = json.load(f)
        all_embeddings = checkpoint.get("embeddings", [])
        start_batch    = checkpoint.get("next_batch", 0)
        print(f"   Resuming from batch {start_batch + 1} ({len(all_embeddings)} embeddings already done)")

    # =====================================================
    # Build batches
    # =====================================================
    texts         = [c["text"] for c in chunks]
    all_batches   = list(batchify(texts, BATCH_SIZE))
    total_batches = len(all_batches)

    # Skip already-done batches
    remaining_batches = all_batches[start_batch:]

    # =====================================================
    # Generate embeddings
    # =====================================================
    print(f"\n⚙️  Generating embeddings... ({len(remaining_batches)} batches remaining)\n")

    # Persistent backoff state shared across batches
    backoff_state = {"delay": BATCH_DELAY}

    for i, batch in enumerate(remaining_batches):
        batch_index = start_batch + i + 1   # 1-based for display

        print(f"  🔹 Batch {batch_index}/{total_batches}  "
              f"(delay={backoff_state['delay']:.1f}s)", flush=True)

        try:
            embeddings = embed_batch_with_retry(client, batch, batch_index, backoff_state)
        except RuntimeError as e:
            print(f"\n🛑  {e}")
            print(f"   Progress saved to checkpoint. Re-run to resume.")
            _save_checkpoint(start_batch + i, all_embeddings)
            return []

        all_embeddings.extend(embeddings)

        # Save checkpoint every N batches
        if batch_index % CHECKPOINT_EVERY == 0:
            _save_checkpoint(batch_index, all_embeddings)
            print(f"  💾 Checkpoint saved ({batch_index}/{total_batches})")

        # Polite delay between successful batches
        time.sleep(backoff_state["delay"])

    # =====================================================
    # Attach embeddings to chunks
    # =====================================================
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    # =====================================================
    # Save final output
    # =====================================================
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Clean up checkpoint on success
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        print("🗑️  Checkpoint cleaned up.")

    # =====================================================
    # Stats
    # =====================================================
    print("\n" + "=" * 50)
    print(f"✅ Embeddings created : {len(all_embeddings)}")
    print(f"📏 Vector dimension   : {len(all_embeddings[0])}")
    print(f"💾 Saved to           : {OUTPUT_PATH}")

    return chunks


# =========================================================
# Checkpoint helpers
# =========================================================
def _save_checkpoint(next_batch: int, embeddings: list):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"next_batch": next_batch, "embeddings": embeddings}, f)


# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    embed_chunks()