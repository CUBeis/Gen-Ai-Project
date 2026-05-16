#!/usr/bin/env python3
"""
Run the full Rag/ data pipeline from the Backend package.

Usage (from Backend/):
  python -m app.rag.scripts.run_clinical_pipeline --pipeline
  python -m app.rag.scripts.run_clinical_pipeline --chat
"""
import argparse
import sys
from pathlib import Path

# Ensure Rag/ modules are importable
_REPO = Path(__file__).resolve().parents[4]
_RAG = _REPO / "Rag"
if str(_RAG) not in sys.path:
    sys.path.insert(0, str(_RAG))


def main():
    parser = argparse.ArgumentParser(description="Nerve AI clinical RAG pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pipeline", action="store_true")
    group.add_argument("--ingest", action="store_true")
    group.add_argument("--chunk", action="store_true")
    group.add_argument("--embed", action="store_true")
    group.add_argument("--upload", action="store_true")
    group.add_argument("--chat", action="store_true")
    args = parser.parse_args()

    if args.pipeline:
        from main import run_pipeline
        run_pipeline()
    elif args.ingest:
        from data_ingestion import run
        run()
    elif args.chunk:
        from semantic_chunking import run
        run()
    elif args.embed:
        from embedding import embed_chunks
        embed_chunks()
    elif args.upload:
        from vector_database import upload
        upload()
    elif args.chat:
        from chatbot import run_cli
        run_cli()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
