#!/bin/bash
# =============================================================================
# Compress & Compare — Quality Evaluation
#
# Runs lm-eval academic benchmarks on the original and quantized models
# to measure quality degradation from quantization.
#
# Benchmarks: HellaSwag (common sense), ARC-Easy (science reasoning)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
mkdir -p "$RESULTS_DIR"

MODELS=(
    "/models/llama-3.1-8b-instruct"
)

# Add quantized models if they exist
if [ -d "/models/llama-3.1-8b-instruct-gptq-4bit" ]; then
    MODELS+=("/models/llama-3.1-8b-instruct-gptq-4bit")
else
    echo "NOTE: GPTQ model not found. Run quantize_gptq.py first."
fi

if [ -d "/models/llama-3.1-8b-instruct-awq-4bit" ]; then
    MODELS+=("/models/llama-3.1-8b-instruct-awq-4bit")
else
    echo "NOTE: AWQ model not found. Run quantize_awq.py first."
fi

TASKS="hellaswag,arc_easy"

echo "============================================="
echo "  Compress & Compare — Quality Evaluation"
echo "  Tasks: $TASKS"
echo "  Models: ${#MODELS[@]}"
echo "============================================="

for model in "${MODELS[@]}"; do
    model_name=$(basename "$model")
    output_path="${RESULTS_DIR}/quality_${model_name}.json"

    echo ""
    echo "--- Evaluating: $model_name ---"

    lm_eval --model vllm \
        --model_args "pretrained=${model}" \
        --tasks "$TASKS" \
        --batch_size auto \
        --output_path "$output_path" \
        2>&1 | tee "${RESULTS_DIR}/quality_${model_name}.log"

    echo "  Results saved to: $output_path"
done

echo ""
echo "============================================="
echo "  Quality evaluation complete!"
echo "  Results: ${RESULTS_DIR}/quality_*.json"
echo ""
echo "  Next: bash benchmark_all.sh"
echo "============================================="
