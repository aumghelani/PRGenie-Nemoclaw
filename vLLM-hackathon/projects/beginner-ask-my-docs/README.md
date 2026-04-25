# Ask My Docs — RAG-Powered Q&A App

**Level:** Beginner | **Tier:** 1 (App Builder) | **GPU:** 1x L40S (48 GB)

Build a document Q&A application that lets users upload files and ask
natural-language questions. Documents are chunked, embedded, and stored in
ChromaDB. When a user asks a question, relevant chunks are retrieved and passed
as context to Llama 3.1 8B running on vLLM.

---

## Quick Start

```bash
# 1. Make sure vLLM is running
bash /workspace/start_vllm_server.sh

# 2. (In a new terminal) Ingest the sample documents
python3 ingest.py

# 3. Launch the Gradio app
python3 app.py
```

Open **http://localhost:7860** in your browser. You can now ask questions about
the sample documents — or upload your own.

---

## How It Works

```
 User Question
      |
      v
 [Embedding Model]  -->  ChromaDB similarity search
      |                         |
      v                         v
 Query embedding          Top-k matching chunks
                                |
                                v
                    Prompt = chunks + question
                                |
                                v
                    vLLM (Llama 3.1 8B)
                                |
                                v
                          Answer displayed
```

### Components

| Component | What it does | Pre-installed? |
|---|---|---|
| **vLLM** | Serves Llama 3.1 8B as an OpenAI-compatible API | Yes |
| **ChromaDB** | Vector store for document embeddings | Yes |
| **sentence-transformers** | Generates embeddings via BGE-small | Yes |
| **LangChain** | Chains retrieval + LLM together | Yes |
| **Gradio** | One-line web UI | Yes |

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Main application — Gradio UI + RAG pipeline |
| `ingest.py` | Ingests documents from `sample-docs/` into ChromaDB |
| `sample-docs/` | Example documents to test with |

---

## Ideas to Extend

- **Add PDF support:** Use `PyPDFLoader` from LangChain
- **Chat memory:** Maintain conversation history across questions
- **Source citations:** Show which document chunks were used in the answer
- **Custom system prompt:** Let users set the persona (e.g., "Answer as a senior engineer")
- **Multiple collections:** Separate vector stores per project/topic

---

## Configuration

The app connects to vLLM at `http://localhost:8000/v1`. If you changed the
port, set the `VLLM_BASE_URL` environment variable:

```bash
VLLM_BASE_URL=http://localhost:9000/v1 python3 app.py
```
