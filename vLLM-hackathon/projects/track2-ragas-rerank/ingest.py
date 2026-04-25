"""
Chunk + embed documents into ChromaDB via LlamaIndex.
"""

import argparse
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", required=True, help="Directory of source docs")
    parser.add_argument("--persist", default="./chroma_db", help="ChromaDB persist dir")
    parser.add_argument("--collection", default="track2_docs")
    parser.add_argument("--embedding-model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=64)
    args = parser.parse_args()

    print(f"[1/4] Loading docs from {args.docs}...")
    docs = SimpleDirectoryReader(input_dir=args.docs, recursive=True).load_data()
    print(f"  Loaded {len(docs)} docs")

    print(f"[2/4] Initializing embedding model ({args.embedding_model})...")
    embed_model = HuggingFaceEmbedding(model_name=args.embedding_model)

    print(f"[3/4] Opening ChromaDB at {args.persist}...")
    client = chromadb.PersistentClient(path=args.persist)
    collection = client.get_or_create_collection(args.collection)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print(f"[4/4] Chunking (size={args.chunk_size}, overlap={args.chunk_overlap}) and embedding...")
    splitter = SentenceSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    index = VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=[splitter],
    )

    count = collection.count()
    print(f"\n✓ Ingested {count} chunks into collection '{args.collection}'")
    print(f"  Query with: python3 query_with_reranker.py 'your question'")


if __name__ == "__main__":
    main()
