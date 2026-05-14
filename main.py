import argparse
import sys


def run_pipeline():
    """Run the full data pipeline: ingest → chunk → embed → upload."""
    print("\n" + "=" * 60)
    print("Nerve AI — Full Pipeline")
    print("=" * 60)

    print("\nData Ingestion...")
    from data_ingestion import run as ingest
    ingest()

    print("\nChunking...")
    from semantic_chunking import run as chunk
    chunk()

    print("\nEmbedding...")
    from embedding import embed_chunks as embed
    embed()

    print("\nUploading to ChromaDB...")
    from vector_database import upload
    upload()

    print("\n" + "=" * 60)
    print("Pipeline complete! You can now run: python main.py --chat")
    print("=" * 60)


def run_ingest():
    from data_ingestion import run
    run()


def run_chunk():
    from semantic_chunking import run
    run()


def run_embed():
    from embedding import embed_chunks
    embed_chunks()


def run_upload():
    from vector_database import upload
    upload()


def run_chat():
    from chatbot import run_cli
    run_cli()


def run_eval(kind: str):
    kind = kind.lower()
    if kind == "retrieval":
        from evaluation.retrieval_evaluation import run
        run()
    elif kind == "generation":
        from evaluation.generation_evaluation import run
        run()
    elif kind == "ragas":
        from evaluation.ragas_evaluation import run
        run()
    else:
        print(f"Unknown evaluation type: '{kind}'")
        print("   Choose from: retrieval | generation | ragas")
        sys.exit(1)


def print_config():
    from config import print_config
    print_config()


# =========================================================
# CLI
# =========================================================
def main():
    parser = argparse.ArgumentParser(
        description="Nerve AI — Clinical RAG Chatbot",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ingest",    action="store_true", help="Step 1: Fetch data from Wikipedia & OpenFDA")
    group.add_argument("--chunk",     action="store_true", help="Step 2: Chunk documents")
    group.add_argument("--embed",     action="store_true", help="Step 3: Generate Cohere embeddings")
    group.add_argument("--upload",    action="store_true", help="Step 4: Upload embedded chunks to ChromaDB")
    group.add_argument("--pipeline",  action="store_true", help="Run all pipeline steps (1–4) in sequence")
    group.add_argument("--chat",      action="store_true", help="Launch the CLI chatbot")
    group.add_argument("--config",    action="store_true", help="Print current configuration")
    group.add_argument(
        "--eval",
        metavar="TYPE",
        help="Run evaluation: retrieval | generation | ragas",
    )

    args = parser.parse_args()

    if args.pipeline:
        run_pipeline()
    elif args.ingest:
        run_ingest()
    elif args.chunk:
        run_chunk()
    elif args.embed:
        run_embed()
    elif args.upload:
        run_upload()
    elif args.eval:
        run_eval(args.eval)
    elif args.config:
        print_config()
    else:
        # Default: launch chatbot
        run_chat()


if __name__ == "__main__":
    main()
