#!/bin/bash
# Install dependencies and fetch EAGLE / Medusa weights for the Speculators Zoo.
set -euo pipefail

echo "============================================="
echo "  Track 3 — Speculators Zoo install"
echo "============================================="

# --- IBM Speculators v0.3.0 ---
echo "[1/3] Installing IBM Speculators..."
pip install --break-system-packages -q "speculators==0.3.0" || \
    pip install --break-system-packages -q "git+https://github.com/IBM/speculators.git@v0.3.0"

# --- EAGLE weights ---
echo "[2/3] Downloading EAGLE weights for Llama 3.1 70B..."
python3 - << 'PY'
from huggingface_hub import snapshot_download
# Community-trained EAGLE heads on Llama 3.1. Swap for your own if you train one.
snapshot_download(
    "yuhuili/EAGLE-LLaMA3.1-Instruct-70B",
    local_dir="/models/eagle-llama-3.1-70b",
    ignore_patterns=["*.bin"],  # prefer safetensors
)
PY

# --- Medusa weights ---
echo "[3/3] Downloading Medusa heads for Llama 3.1 70B..."
python3 - << 'PY'
from huggingface_hub import snapshot_download
# Community Medusa heads — verify availability; if missing, the community
# sometimes publishes them under the model author's account.
try:
    snapshot_download(
        "FasterDecoding/medusa-llama-3.1-70b",
        local_dir="/models/medusa-llama-3.1-70b",
    )
except Exception as e:
    print(f"Medusa weights not found: {e}")
    print("Skipping Medusa — serve_configs/medusa.sh will not work until weights are provided.")
PY

echo ""
echo "✓ Done. Try:"
echo "  bash serve_configs/eagle.sh    # serve with EAGLE"
echo "  python3 measure_acceptance.py --all"
