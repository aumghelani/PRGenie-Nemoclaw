"""
Quantize to MXFP4 using LLM Compressor.

MXFP4 is a shared-scale 4-bit floating-point format. Smaller than INT4,
better-behaved on accuracy in many cases. Requires a recent LLM Compressor
and vLLM ≥ 0.8.

Usage:
    python3 quantize_mxfp4.py --model meta-llama/Llama-3.1-8B-Instruct \\
        --output /models/llama-3.1-8b-instruct-mxfp4
"""

import argparse

from llmcompressor.modifiers.quantization import QuantizationModifier
from llmcompressor.transformers import oneshot
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration-samples", type=int, default=256)
    args = parser.parse_args()

    print(f"[1/3] Loading {args.model}...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, device_map="auto", torch_dtype="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    print("[2/3] Running MXFP4 quantization...")
    # W4A16 with MXFP4 weight encoding — activations stay in FP16.
    # Requires llm-compressor with MXFP4 support.
    recipe = QuantizationModifier(
        targets="Linear",
        scheme="MXFP4_A16",   # schema name may shift; check llm-compressor release notes
        ignore=["lm_head"],
    )

    oneshot(
        model=model,
        dataset="ultrachat_200k",
        recipe=recipe,
        output_dir=args.output,
        num_calibration_samples=args.calibration_samples,
        max_seq_length=2048,
    )

    print(f"\n[3/3] ✓ MXFP4 model saved to {args.output}")
    print("Note: requires vLLM ≥ 0.8 to serve. Try:")
    print(f"  python3 -m vllm.entrypoints.openai.api_server --model {args.output} "
          f"--quantization mxfp4 --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
