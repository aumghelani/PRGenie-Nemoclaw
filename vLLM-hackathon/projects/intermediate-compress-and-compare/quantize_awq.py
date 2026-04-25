"""
Compress & Compare — Quantize Llama 3.1 8B to AWQ 4-bit.

AWQ (Activation-Aware Weight Quantization) identifies salient weight channels
by analyzing activation magnitudes, then protects those channels during
quantization. This often gives better quality than naive round-to-nearest.

Usage:
    python3 quantize_awq.py

Expected time: 10-20 minutes on 2x A100
Expected output size: ~4 GB (vs ~16 GB original)
"""

import time

from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

MODEL_PATH = "/models/llama-3.1-8b-instruct"
OUTPUT_PATH = "/models/llama-3.1-8b-instruct-awq-4bit"


def main():
    print("=" * 55)
    print("  AWQ 4-bit Quantization")
    print(f"  Input:  {MODEL_PATH}")
    print(f"  Output: {OUTPUT_PATH}")
    print("=" * 55)

    # AWQ quantization config
    quant_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM",
    }

    print(f"\nConfig: {quant_config}")

    # Load model for AWQ quantization
    print("\n[1/3] Loading model...")
    model = AutoAWQForCausalLM.from_pretrained(MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

    # Run quantization
    print("[2/3] Running AWQ quantization...")
    start = time.time()

    model.quantize(
        tokenizer,
        quant_config=quant_config,
    )

    elapsed = time.time() - start
    print(f"  Quantization took {elapsed / 60:.1f} minutes")

    # Save
    print(f"[3/3] Saving to {OUTPUT_PATH}...")
    model.save_quantized(OUTPUT_PATH)
    tokenizer.save_pretrained(OUTPUT_PATH)

    print(f"\nAWQ model saved to: {OUTPUT_PATH}")
    print("\nNext steps:")
    print("  bash evaluate_quality.sh        # Measure quality loss")
    print("  bash benchmark_all.sh           # Measure speed gain")


if __name__ == "__main__":
    main()
