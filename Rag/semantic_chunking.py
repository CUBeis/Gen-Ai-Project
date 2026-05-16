import json
import re
import uuid

from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter


# =========================================================
# Paths
# =========================================================
INGESTED_PATH = Path("data/processed/ingested_docs.json")

DISEASES_DIR = Path("data/raw/diseases")
DRUGS_DIR = Path("data/raw/openfda")

OUTPUT_PATH = Path("data/processed/chunks.json")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


# =========================================================
# Chunk Settings
# =========================================================
CHUNK_SIZE = 512
CHUNK_OVERLAP = 100


# =========================================================
# Cleaning
# =========================================================
def clean_text(text: str) -> str:

    if not text:
        return ""

    # Remove wikipedia references [1] [2]
    text = re.sub(r"\[\d+\]", "", text)

    # Remove excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


# =========================================================
# Load JSON File
# =========================================================
def load_json(path: Path):

    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =========================================================
# Load Ingested Docs
# =========================================================
def load_ingested_docs() -> list[dict]:

    if not INGESTED_PATH.exists():

        print(f"  ℹ️ {INGESTED_PATH} not found")
        return []

    docs = load_json(INGESTED_PATH)

    print(f"  📄 ingested_docs : {len(docs)} docs")

    return docs


# =========================================================
# Load Directory Docs
# =========================================================
def load_directory_docs(directory: Path, label: str) -> list[dict]:

    json_files = sorted(directory.glob("*.json"))

    if not json_files:

        print(f"  ⚠️ No files found in {directory}")
        return []

    docs = []

    for path in json_files:

        try:

            docs.append(load_json(path))

        except Exception as e:

            print(f"  ❌ Failed loading {path.name}: {e}")

    print(f"  📂 {label:<15}: {len(docs)} docs")

    return docs


# =========================================================
# Chunk Document
# =========================================================
def chunk_document(
    doc: dict,
    splitter: RecursiveCharacterTextSplitter
) -> list[dict]:

    text = clean_text(doc.get("text", ""))

    if not text:
        return []

    raw_chunks = splitter.split_text(text)

    source = doc.get("source", "unknown")

    chunks = []

    for i, chunk_text in enumerate(raw_chunks):

        chunk = {

            # =================================================
            # IDs
            # =================================================
            "id": str(uuid.uuid4()),

            "chunk_id": (
                f"{source}__chunk_{i}"
            ),

            # =================================================
            # Metadata
            # =================================================
            "source": source,

            "source_type": doc.get(
                "source_type",
                "unknown"
            ),

            "entity_name": doc.get(
                "entity_name"
            ),

            "entity_type": doc.get(
                "entity_type"
            ),

            "url": doc.get("url"),

            "page": doc.get("page"),

            "row_index": doc.get("row_index"),

            # =================================================
            # Chunk Info
            # =================================================
            "chunk_index": i,

            "total_chunks": len(raw_chunks),

            # =================================================
            # Content
            # =================================================
            "text": chunk_text,
        }

        chunks.append(chunk)

    return chunks


# =========================================================
# Main
# =========================================================
def run() -> list[dict]:

    print("\n" + "=" * 60)
    print("🔪 Chunking Documents")
    print("=" * 60)

    # =====================================================
    # Load Sources
    # =====================================================
    ingested_docs = load_ingested_docs()

    disease_docs = load_directory_docs(
        DISEASES_DIR,
        "diseases"
    )

    drug_docs = load_directory_docs(
        DRUGS_DIR,
        "drugs"
    )

    all_docs = (
        ingested_docs +
        disease_docs +
        drug_docs
    )

    if not all_docs:

        print("\n❌ No documents found")
        return []

    print(f"\n📦 Total documents : {len(all_docs)}")

    # =====================================================
    # Splitter
    # =====================================================
    splitter = RecursiveCharacterTextSplitter(

        chunk_size=CHUNK_SIZE,

        chunk_overlap=CHUNK_OVERLAP,

        separators=[
            "\n\n",
            "\n",
            ". ",
            "،",
            " "
        ],
    )

    # =====================================================
    # Chunking
    # =====================================================
    all_chunks = []

    for doc in all_docs:

        chunks = chunk_document(
            doc,
            splitter
        )

        all_chunks.extend(chunks)

    # =====================================================
    # Save
    # =====================================================
    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    # =====================================================
    # Stats
    # =====================================================
    disease_chunks = [
        c for c in all_chunks
        if c["source_type"] == "disease_wiki"
    ]

    drug_chunks = [
        c for c in all_chunks
        if c["source_type"] == "drug_label"
    ]

    other_chunks = [
        c for c in all_chunks
        if c["source_type"]
        not in ["disease_wiki", "drug_label"]
    ]

    print("\n" + "=" * 60)

    print(f"📊 Total chunks        : {len(all_chunks)}")

    print(
        f"   ├─ Disease chunks  : "
        f"{len(disease_chunks)}"
    )

    print(
        f"   ├─ Drug chunks     : "
        f"{len(drug_chunks)}"
    )

    print(
        f"   └─ Other chunks    : "
        f"{len(other_chunks)}"
    )

    print(f"\n💾 Saved to:")
    print(f"   {OUTPUT_PATH}")

    print("\n👉 Next Step:")
    print("   Run: python 9c_embedding.py")

    return all_chunks


# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":

    run()