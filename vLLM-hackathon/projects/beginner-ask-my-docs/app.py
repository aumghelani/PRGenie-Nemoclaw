"""
Ask My Docs — RAG-powered Q&A with Gradio UI.

Retrieves relevant document chunks from ChromaDB and sends them as context
to Llama 3.1 8B running on vLLM to answer the user's question.

Prerequisites:
    1. vLLM server running:  bash /workspace/start_vllm_server.sh
    2. Documents ingested:   python3 ingest.py

Usage:
    python3 app.py
    # Open http://localhost:7860
"""

import os
import chromadb
import gradio as gr
import httpx
from sentence_transformers import SentenceTransformer

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chromadb")
COLLECTION_NAME = "hackathon_docs"
EMBEDDING_MODEL = "/models/bge-small-en"
TOP_K = 4

# --- Load models and stores at startup ---

print("Loading embedding model...")
embedder = SentenceTransformer(EMBEDDING_MODEL)

print("Connecting to ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
try:
    collection = chroma_client.get_collection(COLLECTION_NAME)
    print(f"  Collection '{COLLECTION_NAME}' loaded ({collection.count()} chunks)")
except ValueError:
    print(f"  Collection '{COLLECTION_NAME}' not found. Run 'python3 ingest.py' first.")
    raise SystemExit(1)


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """Retrieve the most relevant document chunks for a query."""
    query_embedding = embedder.encode([query], normalize_embeddings=True).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )
    chunks = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "score": 1 - distance,  # cosine similarity
        })
    return chunks


def ask(question: str, history: list) -> str:
    """RAG pipeline: retrieve context, build prompt, call vLLM."""
    if not question.strip():
        return "Please enter a question."

    # Step 1: Retrieve relevant chunks
    chunks = retrieve(question)

    # Step 2: Build the augmented prompt
    context_block = "\n\n---\n\n".join(
        f"[Source: {c['source']}] (relevance: {c['score']:.2f})\n{c['text']}"
        for c in chunks
    )

    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided "
        "document context. Use ONLY the context below to answer. If the context "
        "does not contain enough information, say so clearly.\n\n"
        f"## Retrieved Context\n\n{context_block}"
    )

    # Step 3: Call vLLM
    messages = [{"role": "system", "content": system_prompt}]
    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": question})

    try:
        r = httpx.post(
            f"{VLLM_BASE_URL}/chat/completions",
            json={
                "model": "/models/llama-3.1-8b-instruct",
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.2,
            },
            timeout=60,
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"]
    except httpx.ConnectError:
        return (
            "Cannot connect to vLLM server. "
            "Make sure it's running: bash /workspace/start_vllm_server.sh"
        )
    except Exception as e:
        return f"Error calling vLLM: {e}"

    # Step 4: Append sources
    sources = sorted(set(c["source"] for c in chunks))
    source_line = f"\n\n---\n*Sources: {', '.join(sources)}*"
    return answer + source_line


# --- Gradio UI ---

with gr.Blocks(title="Ask My Docs", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Ask My Docs")
    gr.Markdown(
        "Ask questions about your documents. Powered by **Llama 3.1 8B** "
        "(vLLM) + **ChromaDB** retrieval."
    )

    chatbot = gr.Chatbot(height=480, label="Conversation")
    msg = gr.Textbox(
        placeholder="Ask a question about your documents...",
        label="Your question",
        scale=4,
    )
    clear = gr.ClearButton([msg, chatbot], value="Clear chat")

    def respond(message, chat_history):
        answer = ask(message, chat_history)
        chat_history.append((message, answer))
        return "", chat_history

    msg.submit(respond, [msg, chatbot], [msg, chatbot])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
