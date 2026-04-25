# Brev Launchable Configuration — Tier 1: App & Inference Builder

Use these settings when creating the Launchable in the Brev Console.

## Step 1: Files & Runtime
- **Code source:** Git repository → (your hackathon starter repo, or empty sandbox)
- **Runtime mode:** VM Mode (Ubuntu 22.04 with Docker/Python/CUDA)

## Step 2: Environment Configuration
- **Setup script:** Paste contents of `setup.sh` from this directory
- Full SSH access enabled

## Step 3: Jupyter & Networking
- **Jupyter:** Enabled (JupyterLab one-click)
- **Networking:**
  - Port 8000 (vLLM API) — Cloudflare tunnel
  - Port 8080 (App scaffold) — Cloudflare tunnel

## Step 4: Compute Selection
- **GPU:** 1× NVIDIA L40S (48GB VRAM)
- **Disk:** 100GB (model weights ~16GB + tools + workspace)
- **Filter by:** Price (L40S is most cost-effective for this tier)

## Step 5: Final Review
- **Name:** `toa-hackathon-app-builder`
- **Visibility:** Link Sharing (attendees get a direct URL)
- **Description:** "TOA vLLM/LLM-D Hackathon — App & Inference Builder. Pre-loaded with Llama 3.1 8B, vLLM, LangChain, ChromaDB, and a FastAPI scaffold."

## Tracks Served
- Track 2: RAG on Open Inference
- Track 5: BYOP — Build Your Own Product
- Track 6: Performance Tuning & Evaluation (Starter lane)
