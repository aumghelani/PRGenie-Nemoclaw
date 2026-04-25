"""
Compress & Compare — Quantize Llama 3.1 8B to GPTQ 4-bit.

Uses llm-compressor (already installed on Tier 2) to run GPTQ calibration
and produce a quantized model that vLLM can serve directly.

GPTQ uses second-order (Hessian) information to minimize quantization error
per layer. It requires a calibration dataset to measure activation patterns.

Usage:
    python3 quantize_gptq.py
    python3 quantize_gptq.py --num-samples 512 --seq-length 4096

Expected time: 15-30 minutes on 2x A100
Expected output size: ~4 GB (vs ~16 GB original)
"""

import argparse
import time

from llmcompressor.modifiers.quantization import GPTQModifier
from llmcompressor.transformers import oneshot
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "/models/llama-3.1-8b-instruct"
OUTPUT_PATH = "/models/llama-3.1-8b-instruct-gptq-4bit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-samples", type=int, default=256,
                        help="Number of calibration samples")
    parser.add_argument("--seq-length", type=int, default=2048,
                        help="Max sequence length for calibration")
    args = parser.parse_args()

    print("=" * 55)
    print("  GPTQ 4-bit Quantization")
    print(f"  Input:  {MODEL_PATH}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Calibration: {args.num_samples} samples, {args.seq_length} seq len")
    print("=" * 55)

    # Load the full-precision model
    print("\n[1/3] Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH, device_map="auto", torch_dtype="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    # Define the quantization recipe
    # W4A16 = 4-bit weights, 16-bit activations
    # ignore lm_head to preserve output quality
    recipe = GPTQModifier(
        targets="Linear",
        scheme="W4A16",
        ignore=["lm_head"],
    )

    # Run quantization with calibration
    print("[2/3] Running GPTQ quantization (this takes a while)...")
    start = time.time()

    oneshot(
        model=model,
        dataset="ultrachat_200k",
        recipe=recipe,
        output_dir=OUTPUT_PATH,
        num_calibration_samples=args.num_samples,
        max_seq_length=args.seq_length,
    )

    elapsed = time.time() - start
    print(f"[3/3] Quantization complete in {elapsed / 60:.1f} minutes")

    print(f"\nQuantized model saved to: {OUTPUT_PATH}")
    print("\nNext steps:")
    print("  python3 quantize_awq.py         # Also create AWQ variant")
    print("  bash evaluate_quality.sh        # Measure quality loss")
    print("  bash benchmark_all.sh           # Measure speed gain")


if __name__ == "__main__":
    main()
