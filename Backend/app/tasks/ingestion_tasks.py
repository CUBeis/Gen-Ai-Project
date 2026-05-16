"""
app/tasks/ingestion_tasks.py
────────────────────────────
Background tasks for RAG document ingestion and chunking.
"""
import structlog
from pathlib import Path
from app.tasks.celery_app import celery_app
from app.rag.ingestion.pdf_loader import PDFLoader
from app.rag.ingestion.csv_loader import CSVLoader
from app.rag.ingestion.chunker import Chunker
from app.rag.embeddings.local_embedder import LocalEmbedder
import chromadb

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="ingestion.process_document",
    bind=True,
    max_retries=3,
)
def process_document_task(self, file_path: str, collection_name: str = "clinical_knowledge"):
    """
    Background task: Process a document (PDF/CSV) through RAG pipeline.

    Steps:
      1. Load document
      2. Chunk content
      3. Generate embeddings
      4. Store in ChromaDB
    """
    import asyncio

    try:
        asyncio.run(_process_document_impl(file_path, collection_name))
    except Exception as exc:
        logger.error(
            "ingestion.process_failed",
            file_path=file_path,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=60)


async def _process_document_impl(file_path: str, collection_name: str) -> None:
    """Process document through RAG pipeline (async implementation)."""
    path = Path(file_path)

    if not path.exists():
        logger.error("ingestion.file_not_found", file_path=file_path)
        raise FileNotFoundError(f"Document not found: {file_path}")

    logger.info("ingestion.start", file_path=file_path, collection=collection_name)

    # Load document
    if path.suffix.lower() == ".pdf":
        loader = PDFLoader()
        documents = await loader.load(file_path)
    elif path.suffix.lower() == ".csv":
        loader = CSVLoader()
        documents = await loader.load(file_path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    if not documents:
        logger.warning("ingestion.no_documents", file_path=file_path)
        return

    logger.info("ingestion.loaded", file_path=file_path, doc_count=len(documents))

    # Chunk documents
    chunker = Chunker()
    chunks = chunker.chunk(documents)
    logger.info("ingestion.chunked", chunk_count=len(chunks))

    # Generate embeddings
    embedder = LocalEmbedder()
    embeddings = [embedder.embed(chunk) for chunk in chunks]

    # Store in ChromaDB
    client = chromadb.PersistentClient()
    collection = client.get_or_create_collection(collection_name)

    # Prepare metadata
    metadatas = [
        {
            "source": str(path),
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # Add to collection
    collection.add(
        embeddings=embeddings,
        metadatas=metadatas,
        documents=chunks,
        ids=[f"{path.stem}_{i}" for i in range(len(chunks))],
    )

    logger.info(
        "ingestion.complete",
        file_path=file_path,
        collection=collection_name,
        chunks_stored=len(chunks),
    )


@celery_app.task(name="ingestion.reindex_all")
def reindex_all_documents_task():
    """Periodic task: Rebuild all RAG collections from scratch."""
    import asyncio

    async def _reindex():
        from app.core.config import settings

        # Clear existing collections
        client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        try:
            client.delete_collection(settings.CHROMA_CLINICAL_COLLECTION)
        except:
            pass

        logger.info("ingestion.reindex_start")

        # Scan documents directory (if it exists)
        docs_dir = Path("./data/documents")
        if docs_dir.exists():
            for file_path in docs_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".csv"]:
                    try:
                        await _process_document_impl(str(file_path), settings.CHROMA_CLINICAL_COLLECTION)
                    except Exception as exc:
                        logger.error(
                            "ingestion.reindex_file_error",
                            file_path=str(file_path),
                            error=str(exc),
                        )

        logger.info("ingestion.reindex_complete")

    asyncio.run(_reindex())
