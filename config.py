import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =========================================================
# Project Paths
# =========================================================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DISEASES_DIR = RAW_DATA_DIR / "diseases"
OPENFDA_DIR = RAW_DATA_DIR / "openfda"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHROMA_DB_PATH = PROJECT_ROOT / "chroma_db"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
DISEASES_DIR.mkdir(exist_ok=True)
OPENFDA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)
CHROMA_DB_PATH.mkdir(exist_ok=True)
EVALUATION_DIR.mkdir(exist_ok=True)

# =========================================================
# API Keys (loaded from .env)
# =========================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Validate critical API keys
if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY not found in .env file")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")

# =========================================================
# LLM Models Configuration
# =========================================================
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embed-multilingual-v3.0")
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank-multilingual-v3.0")

# =========================================================
# API Endpoints
# =========================================================
OPENFDA_API_URL = os.getenv("OPENFDA_API_URL", "https://api.fda.gov/drug/event.json")
WIKIPEDIA_API_URL = os.getenv("WIKIPEDIA_API_URL", "https://en.wikipedia.org/w/api.php")

# =========================================================
# Retrieval Configuration
# =========================================================
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "15"))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", "5"))
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.5"))  # 0 = diversity, 1 = relevance

# =========================================================
# Text Processing & Chunking
# =========================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "48"))  # For embedding batch processing

# =========================================================
# Chatbot Settings
# =========================================================
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
COLLECTION_NAME = "medical_rag"

# =========================================================
# ChromaDB Configuration
# =========================================================
CHROMA_DB_PERSIST = os.getenv("PERSIST_DIRECTORY", str(CHROMA_DB_PATH))
CHROMA_PATH = str(CHROMA_DB_PATH)

# =========================================================
# Configuration Summary (for debugging)
# =========================================================
def print_config():
    """Print current configuration (useful for debugging)."""
    cohere_status = "✓ Configured" if COHERE_API_KEY else "✗ NOT SET"
    router_status = "✓ Configured" if OPENROUTER_API_KEY else "✗ NOT SET"
    
    print(f"""
    ===== Clinical RAG Chatbot Configuration =====
    
    API Keys:
    - COHERE_API_KEY: {cohere_status}
    - OPENROUTER_API_KEY: {router_status}
    - OPENAI_API_KEY: {'✓ Configured' if OPENAI_API_KEY else '✗ NOT SET'}
    
    Models:
    - LLM: {LLM_MODEL}
    - Embedding: {EMBEDDING_MODEL}
    - Reranking: {RERANK_MODEL}
    
    Paths:
    - Project Root: {PROJECT_ROOT}
    - Data: {DATA_DIR}
    - ChromaDB: {CHROMA_DB_PATH}
    
    Settings:
    - Chunk Size: {CHUNK_SIZE}
    - Chunk Overlap: {CHUNK_OVERLAP}
    - Top K Retrieval: {RETRIEVE_TOP_K}    - Final Top K: {FINAL_TOP_K}    - Max History: {MAX_HISTORY_MESSAGES}
    
    ============================================
    """)

if __name__ == "__main__":
    print_config()
