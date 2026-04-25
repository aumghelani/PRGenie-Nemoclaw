"""
Download a pre-quantized AWQ model from HuggingFace.

This avoids the need to run quantization yourself — someone has already done
the calibration work and published the compressed weights.

Usage:
    python3 download_quantized.py
"""

from huggingface_hub import snapshot_download

MODEL_ID = "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4"
LOCAL_DIR = "/models/llama-3.1-8b-instruct-awq-int4"


def main():
    print("=" * 50)
    print("  Downloading pre-quantized Llama 3.1 8B (AWQ INT4)")
    print(f"  Source: {MODEL_ID}")
    print(f"  Destination: {LOCAL_DIR}")
    print("=" * 50)
    print()
    print("This is ~4 GB (vs ~16 GB for the full model).")
    print("Should take 1-2 minutes on a fast connection.\n")

    snapshot_download(
        MODEL_ID,
        local_dir=LOCAL_DIR,
        ignore_patterns=["*.pth", "original/**"],
    )

    print(f"\nDone! Quantized model saved to: {LOCAL_DIR}")
    print("Next: bash serve_both.sh")


if __name__ == "__main__":
    main()
