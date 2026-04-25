#!/bin/bash
# =============================================================================
# ZeroClaw Code Assistant Demo — Setup Script
# Installs ZeroClaw + Ollama and pulls a quantized model for local inference.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL="llama3.1:8b-q4_K_M"

echo "============================================="
echo "  ZeroClaw Code Assistant — Setup"
echo "============================================="

# --- Detect OS ---
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "Detected: $OS ($ARCH)"

# --- Install Ollama ---
if command -v ollama &> /dev/null; then
    echo "[1/4] Ollama already installed: $(ollama --version)"
else
    echo "[1/4] Installing Ollama..."
    case "$OS" in
        Darwin)
            if command -v brew &> /dev/null; then
                brew install ollama
            else
                echo "Install Homebrew first: https://brew.sh"
                echo "Or download Ollama from: https://ollama.com/download"
                exit 1
            fi
            ;;
        Linux)
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        *)
            echo "Unsupported OS. Download Ollama from: https://ollama.com/download"
            exit 1
            ;;
    esac
fi

# --- Start Ollama (if not running) ---
echo "[2/4] Ensuring Ollama is running..."
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "  Starting Ollama server..."
    ollama serve &> /dev/null &
    sleep 3
fi

# --- Pull quantized model ---
echo "[3/4] Pulling $MODEL (~4.5GB)..."
echo "  This is a one-time download."
ollama pull "$MODEL"

# --- Install ZeroClaw ---
if command -v zeroclaw &> /dev/null; then
    echo "[4/4] ZeroClaw already installed: $(zeroclaw --version 2>&1 | head -1)"
else
    echo "[4/4] Installing ZeroClaw..."
    case "$OS" in
        Darwin)
            if command -v brew &> /dev/null; then
                brew install zeroclaw
            else
                curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/scripts/bootstrap.sh | bash
            fi
            ;;
        Linux)
            curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/scripts/bootstrap.sh | bash
            ;;
        *)
            echo "Download ZeroClaw from: https://github.com/zeroclaw-labs/zeroclaw/releases"
            exit 1
            ;;
    esac
fi

# --- Copy config and skills ---
echo ""
echo "Setting up ZeroClaw workspace..."
WORKSPACE="$HOME/.zeroclaw/workspace"
mkdir -p "$WORKSPACE/skills"

cp "$SCRIPT_DIR/config.ollama.toml" "$HOME/.zeroclaw/config.toml"
cp "$SCRIPT_DIR"/skills/*.md "$WORKSPACE/skills/"

echo ""
echo "============================================="
echo "  Setup complete!"
echo ""
echo "  Quick start:"
echo "    zeroclaw start"
echo ""
echo "  Try these commands:"
echo "    'explain this code: def fib(n): ...'"
echo "    'refactor this function for readability'"
echo "    'do a security audit of this code'"
echo ""
echo "  Local model:  $MODEL (via Ollama)"
echo "  Cloud model:  Claude Sonnet (set ANTHROPIC_API_KEY for cloud tasks)"
echo ""
echo "  To use vLLM on a GPU instance instead:"
echo "    cp $SCRIPT_DIR/config.vllm.toml ~/.zeroclaw/config.toml"
echo "============================================="
