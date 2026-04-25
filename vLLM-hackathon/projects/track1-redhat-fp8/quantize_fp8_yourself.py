"""
Quantize a model to FP8 (W8A8) using LLM Compressor.

This is calibration-based post-training quantization — no training required.
On an A100, Llama 3.1 8B takes ~15-20 minutes.

Usage:
    python3 quantize_fp8_yourself.py \\
        --model meta-llama/Llama-3.1-8B-Instruct \\
        --output /models/llama-3.1-8b-instruct-fp8-mine
"""

import argparse
from pathlib import Path

from llmcompressor.modifiers.quantization import QuantizationModifier
from llmcompressor.transformers import oneshot
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration-samples", type=int, default=256)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    args = parser.parse_args()

    print(f"[1/3] Loading {args.model}...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, device_map="auto", torch_dtype="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    print(f"[2/3] Running FP8 (W8A8) quantization with {args.calibration_samples} calibration samples...")
    # W8A8 FP8 — both weights and activations in FP8.
    # Skip lm_head because quantizing it hurts quality noticeably.
    recipe = QuantizationModifier(
        targets="Linear",
        scheme="FP8",
        ignore=["lm_head"],
    )

    oneshot(
        model=model,
        dataset="ultrachat_200k",
        recipe=recipe,
        output_dir=args.output,
        num_calibration_samples=args.calibration_samples,
        max_seq_length=args.max_seq_length,
    )

    print(f"\n[3/3] ✓ FP8 model saved to {args.output}")
    print(f"\nServe with:")
    print(f"  python3 -m vllm.entrypoints.openai.api_server \\")
    print(f"      --model {args.output} --host 0.0.0.0 --port 8000")
    print(f"\nCompare to Red Hat's reference quant:")
    print(f"  python3 pull_redhat_models.py --model 8b-fp8")
    print(f"  python3 benchmark_compound.py --compare fp8-redhat fp8-mine")


if __name__ == "__main__":
    main()
