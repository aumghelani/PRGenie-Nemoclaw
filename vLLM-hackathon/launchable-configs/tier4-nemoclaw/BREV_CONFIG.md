# Brev Launchable Configuration — Tier 4: Agentic Edge (Track 5 / NVIDIA GPU Prize)

Use these settings when creating the Launchable in the Brev Console.

## Step 1: Files & Runtime

- **Code source:** Git repository → `https://github.com/holzerjm/vLLM-hackathon` (or your fork)
- **Runtime mode:** VM Mode (Ubuntu 22.04 with Docker/Python/CUDA)
- **Why VM mode:** NemoClaw ships an OpenShell sandbox that needs Docker on the host — not possible in container mode

## Step 2: Environment Configuration

- **Setup script:** Paste contents of `setup.sh` from this directory
- **SSH access:** Enabled (required for `nemoclaw connect` and `openclaw tui`)
- **Environment variables:**
  - `NVIDIA_API_KEY` — only if you want to fall back to the `nvidia-cloud` profile (Nemotron-3-Super-120B)

## Step 3: Jupyter & Networking

- **Jupyter:** Enabled (JupyterLab one-click for notebooks and debugging)
- **Networking:**
  - Port 8000 (vLLM OpenAI-compatible API) — Cloudflare tunnel
  - Port 7860 (Gradio UI for the Starter tier) — Cloudflare tunnel
  - SSH enabled for tmux / openshell workflows

## Step 4: Compute Selection

- **GPU:** 1× NVIDIA A100 80GB (preferred) or 1× H100
- **Why:** The 8B agent backbone fits comfortably on one A100; the extra VRAM gives headroom for KV cache during multi-turn loops and leaves room for a Nemotron-Nano-30B profile if attendees want to compare models
- **Disk:** 200GB (Llama 8B ~16GB + Nemotron 30B ~60GB if pre-cached + Docker layers + workspace)
- **Filter by:** Availability, then price

## Step 5: Final Review

- **Name:** `toa-hackathon-agentic-edge`
- **Visibility:** Link Sharing (attendees get a direct URL)
- **Description:** "TOA vLLM/LLM-D Hackathon — Track 5 (NVIDIA GPU Prize): Agentic Edge powered by NemoClaw. Pre-loaded with vLLM serving Llama 3.1 8B, NemoClaw + OpenShell, agent scaffolds, and benchmarking harness."

## Tracks Served

- **Track 5: Agentic Edge powered by NemoClaw** (NVIDIA GPU Prize)
  - Starter: vibe-code an agent UI with Cursor using the starter template
  - Builder: extend the multi-turn customer support reference agent
  - Deep Tech: steering + latency benchmarking across inference profiles
