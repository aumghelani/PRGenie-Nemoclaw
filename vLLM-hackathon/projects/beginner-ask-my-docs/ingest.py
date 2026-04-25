"""
Document ingestion script for Ask My Docs.

Reads all .md and .txt files from sample-docs/, splits them into chunks,
generates embeddings with BGE-small, and stores them in a ChromaDB collection.

Usage:
    python3 ingest.py                     # Ingest sample-docs/
    python3 ingest.py /path/to/my/docs    # Ingest a custom directory
"""

import os
import sys
import glob
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "sample-docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chromadb")
COLLECTION_NAME = "hackathon_docs"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_MODEL = "/models/bge-small-en"


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def load_documents(docs_dir: str) -> list[dict]:
    """Load all .md and .txt files from a directory."""
    docs = []
    for pattern in ["*.md", "*.txt"]:
        for filepath in glob.glob(os.path.join(docs_dir, pattern)):
            with open(filepath, "r") as f:
                content = f.read()
            docs.append({
                "filename": os.path.basename(filepath),
                "content": content,
            })
    return docs


def main():
    print(f"Loading documents from: {DOCS_DIR}")
    documents = load_documents(DOCS_DIR)
    if not documents:
        print(f"No .md or .txt files found in {DOCS_DIR}")
        sys.exit(1)
    print(f"  Found {len(documents)} document(s)")

    # Chunk documents
    all_chunks = []
    all_ids = []
    all_metadata = []
    for doc in documents:
        chunks = chunk_text(doc["content"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{doc['filename']}::chunk_{i}")
            all_metadata.append({"source": doc["filename"], "chunk_index": i})
    print(f"  Created {len(all_chunks)} chunks")

    # Generate embeddings
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("  Generating embeddings...")
    embeddings = model.encode(all_chunks, show_progress_bar=True, normalize_embeddings=True)

    # Store in ChromaDB
    print(f"Storing in ChromaDB at: {CHROMA_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection if present (fresh ingest)
    try:
        client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=all_ids,
        embeddings=embeddings.tolist(),
        documents=all_chunks,
        metadatas=all_metadata,
    )

    print(f"\nDone! Ingested {len(all_chunks)} chunks into collection '{COLLECTION_NAME}'")
    print("Run 'python3 app.py' to start the Q&A interface.")


if __name__ == "__main__":
    main()
