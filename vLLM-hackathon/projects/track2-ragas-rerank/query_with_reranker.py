"""
Two-stage retrieval: cheap embedding top-50 → expensive cross-encoder rerank → top-5.
Generate the final answer with vLLM.
"""

import argparse
import os
import sys

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb


def build_query_engine(persist_dir: str, collection: str):
    # Vector store
    client = chromadb.PersistentClient(path=persist_dir)
    collection_obj = client.get_collection(collection)
    vector_store = ChromaVectorStore(chroma_collection=collection_obj)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Re-use the same embedding model we ingested with
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # vLLM is OpenAI-compatible
    llm = OpenAILike(
        model=os.getenv("VLLM_MODEL", "/models/llama-3.1-8b-instruct"),
        api_base=os.getenv("VLLM_ENDPOINT", "http://localhost:8000/v1"),
        api_key="not-needed",
        is_chat_model=True,
        temperature=0.2,
        max_tokens=512,
    )

    # Load index and create query engine with reranker
    index = VectorStoreIndex.from_vector_store(
        vector_store, embed_model=embed_model
    )

    reranker = SentenceTransformerRerank(
        model="BAAI/bge-reranker-large",
        top_n=5,           # return top-5 after reranking
    )

    query_engine = index.as_query_engine(
        llm=llm,
        similarity_top_k=50,     # embed-stage fetches 50 candidates
        node_postprocessors=[reranker],   # reranker cuts down to 5
    )
    return query_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+", help="Question to ask")
    parser.add_argument("--persist", default="./chroma_db")
    parser.add_argument("--collection", default="track2_docs")
    args = parser.parse_args()

    question = " ".join(args.query)
    engine = build_query_engine(args.persist, args.collection)

    print(f"Q: {question}\n")
    response = engine.query(question)
    print(f"A: {response}\n")

    print("--- Retrieved (post-rerank) context chunks ---")
    for i, node in enumerate(response.source_nodes, 1):
        score = node.score if node.score is not None else float("nan")
        preview = node.node.get_content()[:140].replace("\n", " ")
        print(f"  [{i}] score={score:.3f}  {preview}...")


if __name__ == "__main__":
    main()
